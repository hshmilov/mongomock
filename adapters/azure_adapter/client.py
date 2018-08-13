import logging
logger = logging.getLogger(f'axonius.{__name__}')

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from msrestazure import azure_cloud as azure


class AzureClient(object):
    DEFAULT_CLOUD = 'Azure Public Cloud'

    def __init__(self, subscription_id, client_id, client_secret, tenant_id, cloud_name=None):
        if cloud_name is None:
            cloud_name = self.DEFAULT_CLOUD
        cloud = self.get_clouds()[cloud_name]
        credentials = ServicePrincipalCredentials(client_id=client_id, secret=client_secret, tenant=tenant_id,
                                                  cloud_environment=cloud)
        self.compute = ComputeManagementClient(credentials, subscription_id, base_url=cloud.endpoints.resource_manager)
        self.network = NetworkManagementClient(credentials, subscription_id, base_url=cloud.endpoints.resource_manager)

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
        return

    def get_virtual_machines(self):
        subnets = {}
        for vm in self.compute.virtual_machines.list_all():
            vm_dict = vm.as_dict()
            vm_dict['network_profile']['network_interfaces'] = [
                self._get_iface_dict(iface, subnets) for iface in vm.network_profile.network_interfaces
            ]
            yield vm_dict

    def _get_iface_dict(self, iface_link, subnets):
        try:
            iface_id = self.split_id(iface_link.id)
            iface = self.network.network_interfaces.get(iface_id['resourceGroups'],
                                                        iface_id['networkInterfaces'])
        except Exception as e:
            if 'was not found' not in str(e):
                logger.exception(f'While getting interface {iface_link.id}')
            iface_dict = iface_link.as_dict()
            iface_dict['error'] = str(e)
            return iface_dict
        iface_dict = iface.as_dict()
        iface_dict['ip_configurations'] = [
            self._expand_ip_configuration_dict(ip_configuration, subnets)
            for ip_configuration in iface.ip_configurations
        ]
        if 'virtual_machine' in iface_dict:
            del iface_dict['virtual_machine']
        return iface_dict

    def _expand_ip_configuration_dict(self, ip_configuration, subnets):
        ip_configuration_dict = ip_configuration.as_dict()
        ip_configuration_dict['public_ip_address'] = \
            self._get_public_ip_address_dict(ip_configuration.public_ip_address)
        ip_configuration_dict['subnet'] = \
            self._get_subnet_dict(ip_configuration.subnet, subnets)
        return ip_configuration_dict

    def _get_public_ip_address_dict(self, ip_address_link):
        try:
            ip_address_id = self.split_id(ip_address_link.id)
            ip_address = self.network.public_ip_addresses.get(ip_address_id['resourceGroups'],
                                                              ip_address_id['publicIPAddresses'])
        except Exception as e:
            if 'was not found' not in str(e):
                logger.exception(f'While getting public ip address {ip_address_link.id}')
            ip_address_dict = ip_address_link.as_dict()
            ip_address_dict['error'] = str(e)
            return ip_address_dict
        ip_address_dict = ip_address.as_dict()
        if 'ip_configuration' in ip_address_dict:
            del ip_address_dict['ip_configuration']
        return ip_address_dict

    def _get_subnet_dict(self, subnet_link, subnets):
        if subnet_link.id in subnets:
            return subnets[subnet_link.id]
        try:
            subnet_id = self.split_id(subnet_link.id)
            subnet = self.network.subnets.get(subnet_id['resourceGroups'], subnet_id['virtualNetworks'],
                                              subnet_id['subnets'])
        except Exception as e:
            if 'was not found' not in str(e):
                logger.exception(f'While getting subnet {subnet_link.id}')
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
