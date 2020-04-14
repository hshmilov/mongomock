import logging
from typing import Optional, Iterable, Tuple

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import VirtualMachine, VirtualMachineScaleSetVM
from azure.mgmt.network import NetworkManagementClient
from msrestazure import azure_cloud as azure

from axonius.clients.rest.connection import RESTConnection
from azure_adapter.consts import RE_VM_RESOURCEGROUP_FROM_ID, RE_VM_RESOURCEGROUP_CG

logger = logging.getLogger(f'axonius.{__name__}')


class AzureClient:
    DEFAULT_CLOUD = 'Azure Public Cloud'

    def __init__(self, subscription_id,
                 client_id, client_secret, tenant_id, cloud_name=None,
                 azure_stack_hub_resource=None, azure_stack_hub_url=None,
                 https_proxy=None, verify_ssl=None):
        if cloud_name is None:
            cloud_name = self.DEFAULT_CLOUD
        cloud = self.get_clouds()[cloud_name]
        proxies = {'https': RESTConnection.build_url(https_proxy).strip('/')} if https_proxy else None

        if azure_stack_hub_url and azure_stack_hub_resource:
            base_url = azure_stack_hub_url
            resource = azure_stack_hub_resource

            logger.info(f'Using Azure Stack Hub - Resource "{resource}" with URL "{base_url}"')
            credentials = ServicePrincipalCredentials(client_id=client_id, secret=client_secret, tenant=tenant_id,
                                                      cloud_environment=cloud, resource=resource,
                                                      proxies=proxies, verify=verify_ssl)
        else:
            base_url = cloud.endpoints.resource_manager
            credentials = ServicePrincipalCredentials(client_id=client_id, secret=client_secret, tenant=tenant_id,
                                                      cloud_environment=cloud, proxies=proxies, verify=verify_ssl)
        self.compute = ComputeManagementClient(credentials, subscription_id, base_url=base_url)
        self.network = NetworkManagementClient(credentials, subscription_id, base_url=base_url)
        if proxies:
            self.network.config.proxies.use_env_settings = False
            self.network.config.proxies.proxies = proxies
            self.compute.config.proxies.use_env_settings = False
            self.compute.config.proxies.proxies = proxies

        if verify_ssl is False:
            self.network.config.connection.verify = False
            self.compute.config.connection.verify = False

    @classmethod
    def get_clouds(cls):
        clouds = {}
        for name in dir(azure):
            item = getattr(azure, name)
            if isinstance(item, azure.Cloud):
                # use a nice name, format example: AZURE_US_GOV_CLOUD -> Azure US Gov Cloud
                clouds[name.replace('_', ' ').title().replace('Us ', 'US ')] = item
        assert cls.DEFAULT_CLOUD in clouds
        return clouds

    def test_connection(self):
        for _ in self.compute.virtual_machines.list_all():
            break
        for _ in self.compute.virtual_machine_scale_sets.list_all():
            break

    def get_virtual_machines(self):
        yield from self._get_vms()
        yield from self._get_scale_set_vms()

    def _get_vms(self):
        subnets = {}
        for vm in self.compute.virtual_machines.list_all():
            try:
                vm_dict = vm.as_dict()
                vm_dict['network_profile']['network_interfaces'] = [
                    self._get_iface_dict(iface, subnets) for iface in vm.network_profile.network_interfaces
                ]
                vm_dict['instance_view'] = self._get_vm_instance_view(vm)
                yield vm_dict
            except Exception:
                logger.exception(f'Failed fetching azure vm')

    def _get_vm_instance_view(self, vm_machine: VirtualMachine) -> Optional[dict]:
        """
        Retrieve a single vm instance_view.
        According to https://stackoverflow.com/a/49375041 this must be retrieved using a separate API because MS
            doesn't really fill the appropriate property in virtual_machines.list_all although documented to.
        """
        try:
            resource_group_match = RE_VM_RESOURCEGROUP_FROM_ID.search(vm_machine.id)
            if not (resource_group_match and (RE_VM_RESOURCEGROUP_CG in resource_group_match.groupdict())):
                logger.warning(f'Failed locating InstanceView of vm {vm_machine.id} due to unexpected VM id format')
                return None
            resource_group_name = resource_group_match[RE_VM_RESOURCEGROUP_CG]
            instance_view = self.compute.virtual_machines.instance_view(resource_group_name=resource_group_name,
                                                                        vm_name=vm_machine.name)
            return instance_view.as_dict()
        except Exception:
            logger.exception(f'Failed locating InstanceView of vm {vm_machine.id}')
            return None

    def _get_scale_set_vms(self):
        """
        compute.virtual_machine_scale_set_vms does not have a list_all() method.
        The scale_set_vms.list() method takes resource_group_name and scale_set_name, so we need to
        get those first.
        """
        subnets = {}
        for scale_set_name, rg_name in self._get_scale_sets_names_and_rg():
            for vm in self.compute.virtual_machine_scale_set_vms.list(rg_name, scale_set_name):
                try:
                    vm_dict = vm.as_dict()
                    vm_dict['network_profile']['network_interfaces'] = [
                        self._get_iface_dict(iface, subnets) for iface in vm.network_profile.network_interfaces
                    ]
                    # Check in case the comment from _get_vm_instance_view does not apply for
                    # azure.mgmt.compute.model.VirtualMachineScaleSetVM objects
                    if not vm.instance_view:
                        vm_dict['instance_view'] = self._get_scale_set_vm_instance_view(
                            vm, scale_set_name, rg_name)
                    yield vm_dict
                except Exception:
                    logger.exception(f'Failed fetching scale set VM for '
                                     f'resource group {rg_name} and name {scale_set_name}')

    def _get_scale_sets_names_and_rg(self) -> Iterable[Tuple[str, str]]:
        """
        Get scale set names, and from each scale set id extract resource group also.
        """
        for scale_set in self.compute.virtual_machine_scale_sets.list_all():
            try:
                scale_set_name = scale_set.name
            except Exception:
                logger.exception(f'Failed fetching azure scale set for scale set vms')
                continue
            try:
                resource_group_match = RE_VM_RESOURCEGROUP_FROM_ID.search(scale_set.id)
                if not (resource_group_match and (RE_VM_RESOURCEGROUP_CG in resource_group_match.groupdict())):
                    logger.warning(f'Failed locating RG of scale set {scale_set.id} '
                                   f'due to unexpected scale set id format')
                    continue
                resource_group_name = resource_group_match[RE_VM_RESOURCEGROUP_CG]
                yield scale_set_name, resource_group_name
            except Exception:
                logger.exception(f'Failed fetching azure scale set name and resource group'
                                 f' for scale set {scale_set.as_dict()}')

    def _get_scale_set_vm_instance_view(self, ss_vm: VirtualMachineScaleSetVM,
                                        ss_name: str, resource_group: str) -> Optional[dict]:
        try:
            return self.compute.virtual_machine_scale_set_vms.get_instance_view(
                resource_group, ss_name, ss_vm.instance_id).as_dict()
        except Exception:
            logger.exception(f'Failed fetching instance view of scale set vm {ss_vm.id}')
            return None

    def _get_iface_dict(self, iface_link, subnets):
        try:
            iface_id = self.split_id(iface_link.id)
            iface = self.network.network_interfaces.get(iface_id['resourceGroups'],
                                                        iface_id['networkInterfaces'])
        except Exception as e:
            if 'was not found' not in str(e):
                logger.exception(f'While getting interface {iface_link}')
            iface_dict = iface_link.as_dict()
            iface_dict['error'] = str(e)
            return iface_dict
        iface_dict = iface.as_dict()
        iface_dict['ip_configurations'] = [
            self._expand_ip_configuration_dict(ip_configuration, subnets)
            for ip_configuration in iface.ip_configurations
        ]
        try:
            nsg_object = iface.network_security_group
            if nsg_object:
                nsg = self._expand_network_security_group(nsg_object.id)
                if nsg:
                    iface_dict['network_security_group'] = nsg
        except Exception:
            logger.exception(f'Error parsing network security group for iface {str(iface_dict)}')
        if 'virtual_machine' in iface_dict:
            del iface_dict['virtual_machine']
        return iface_dict

    def _expand_network_security_group(self, network_security_group_id):
        nsg_dict = self.split_id(network_security_group_id)
        nsg_object = self.network.network_security_groups.get(
            nsg_dict['resourceGroups'], nsg_dict['networkSecurityGroups']
        )
        return nsg_object.as_dict()

    def _expand_ip_configuration_dict(self, ip_configuration, subnets):
        ip_configuration_dict = ip_configuration.as_dict()
        ip_configuration_dict['public_ip_address'] = \
            self._get_public_ip_address_dict(ip_configuration.public_ip_address)
        ip_configuration_dict['subnet'] = \
            self._get_subnet_dict(ip_configuration.subnet, subnets)
        return ip_configuration_dict

    def _get_public_ip_address_dict(self, ip_address_link):
        if not ip_address_link:
            return dict()
        try:
            ip_address_id = self.split_id(ip_address_link.id)
            ip_address = self.network.public_ip_addresses.get(ip_address_id['resourceGroups'],
                                                              ip_address_id['publicIPAddresses'])
        except Exception as e:
            if 'was not found' not in str(e):
                logger.exception(f'While getting public ip address {ip_address_link}')
            ip_address_dict = ip_address_link.as_dict()
            ip_address_dict['error'] = str(e)
            return ip_address_dict
        ip_address_dict = ip_address.as_dict()
        if 'ip_configuration' in ip_address_dict:
            del ip_address_dict['ip_configuration']
        return ip_address_dict

    def _get_subnet_dict(self, subnet_link, subnets):
        if not subnet_link:
            return dict()
        if subnet_link.id in subnets:
            return subnets[subnet_link.id]
        try:
            subnet_id = self.split_id(subnet_link.id)
            subnet = self.network.subnets.get(subnet_id['resourceGroups'], subnet_id['virtualNetworks'],
                                              subnet_id['subnets'])
        except Exception as e:
            if 'was not found' not in str(e):
                logger.exception(f'While getting subnet {subnet_link}')
            subnet_dict = subnet_link.as_dict()
            subnet_dict['error'] = str(e)
            return subnet_dict
        subnet_dict = subnet.as_dict()
        if 'ip_configurations' in subnet_dict:
            del subnet_dict['ip_configurations']
        subnets[subnet_link.id] = subnet_dict
        return subnet_dict

    @staticmethod
    def split_id(raw_id_str):
        """
        split azure id: /subscriptions/ba4aa321-c802-4de2-bb72-ca4c66b5b124/resourceGroups/
            [no new line]               myResourceGroup/providers/Microsoft.Network/publicIPAddresses/win-test-server-ip
        into the identity dict (for easy access): {
            'subscriptions': 'ba4aa321-c802-4de2-bb72-ca4c66b5b124',
            'resourceGroups': 'myResourceGroup',
            'providers': 'Microsoft.Network',
            'publicIPAddresses': 'win-test-server-ip'
        }
        """
        id_dict = {}
        items = raw_id_str.split('/')
        assert items.pop(0) == ''
        while items:
            name = items.pop(0)
            value = items.pop(0)
            id_dict[name] = value
        return id_dict
