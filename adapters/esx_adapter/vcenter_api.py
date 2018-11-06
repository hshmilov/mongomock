import logging

logger = logging.getLogger(f'axonius.{__name__}')
from pyVim import connect
from pyVmomi.VmomiSupport import Enum as pyVmomiEnum
from retrying import retry
from datetime import datetime
from namedlist import namedlist
from pyVmomi import vim

vCenterNode = namedlist(
    'vCenterNode', ['Name', 'Type', ('Children', []), ('Details', None), ('Hardware', None)])


def _is_vmomi_primitive(v):
    """
    Figures out if v is a primitive value according to pyVmomi.

    :param v:
    :return bool:
    """
    primitives = (int, float, bool, str, datetime, pyVmomiEnum)
    return isinstance(v, primitives)


def _take_just_primitives(d):
    """
    Returns only primitive values from d.

    :param dict d:
    :return: dict
    """
    return {k: v for k, v in d.items() if _is_vmomi_primitive(v)}


def rawify_vcenter_data(folder):
    """
    Converts all data to a JSON serializable form (dicts, lists)

    :type folder: vCenterNode
    :param folder: Perhaps the value returned from get_all_vms
    :return: dict
    """
    return vCenterNode(folder.Name, folder.Type,
                       [rawify_vcenter_data(child) for child in folder.Children if child is not None],
                       folder.Details, folder.Hardware)._asdict()


def _should_retry_fetching(exception):
    return isinstance(exception, vim.fault.NoPermission)


class vCenterApi(object):
    """ vCenterApi.py: A wrapper for vCenter SOAP services """

    def __init__(self, host, user, password, verify_ssl=False):
        """
        Ctor
        :param str host: ip or dns of the vcenter server
        :param str user: your username
        :param str password: your password
        :param bool verify_ssl: should we verify SSL or not
        :raise See pyVim documentation for connect
        """
        self._verify_ssl = verify_ssl
        self._host = host
        self._user = user
        self._password = password
        self._connect()
        self.__devices_count = None

    def _connect(self):
        if self._verify_ssl:
            session = connect.Connect(
                self._host, 443, self._user, self._password)
        else:
            session = connect.ConnectNoSSL(
                self._host, 443, self._user, self._password)
        self._session = session

    def _parse_networking(self, vm):
        """
        Parses networking from vm state
        :return: iter(dict)
        """
        guest = getattr(vm, 'guest', None)
        if not guest:
            return []
        guest_net = guest.net
        if guest_net is None:
            return []
        for network in guest_net:
            if network is None:
                continue
            primitives = _take_just_primitives(network.__dict__)
            if network.ipConfig is not None:
                primitives['ipAddresses'] = [_take_just_primitives(addr.__dict__) for addr in
                                             network.ipConfig.ipAddress]
            yield primitives

    def _parse_networking_from_hardware(self, vm_root):
        config = getattr(vm_root, 'config', None)
        if not config:
            return
        network = getattr(config, 'network', None)
        if not network:
            return
        vnic = getattr(network, 'vnic', None)
        if not vnic:
            return
        for network_interface in vnic:
            yield {'mac': network_interface.spec.mac, 'ips': [network_interface.spec.ip.ipAddress]}

    def _parse_host(self, host):
        """
        Parses a ESX host
        :param host: of type pyVmomi.VmomiSupport.vim.ComputeResource
        :return:
        """
        values_to_take = ['totalCpu', 'totalMemory', 'numCpuCores', 'numCpuThreads', 'effectiveCpu', 'effectiveMemory',
                          'numHosts', 'numEffectiveHosts', 'overallStatus']
        details = {k: getattr(host.summary, k, None) for k in values_to_take}

        parsed_hosts = [self._parse_vm_host(x) for x in host.host]

        if len(parsed_hosts) > 1:
            if host._wsdlName != 'ClusterComputeResource':
                logger.warning(f'Host isn\'t a cluster, it\'s a {host._wsdlName} but has {len(parsed_hosts)}')

            return vCenterNode(Name=host.name, Type='Cluster', Children=[
                self._cluster_host_to_vcenter_node(parsed_host, f'{host.name}_{index}')
                for index, parsed_host
                in enumerate(parsed_hosts)
            ], Hardware=details)

        if not parsed_hosts:
            return vCenterNode(Name=host.name, Type='ESXHost', Details={}, Hardware=details)

        if len(parsed_hosts) == 1:
            return vCenterNode(Name=host.name, Type='ESXHost', Details=parsed_hosts[0], Hardware=details)

    @staticmethod
    def _cluster_host_to_vcenter_node(host, alternative_name: str) -> vCenterNode:
        """
        Takes a host (vim.HostSystem) that has been parsed already using _parse_vm_host
        and processes it into a vCenterNode
        :param host: the host from _parse_vm_host
        :param alternative_name: the name to use for the ID if nothing else is available
        """
        return vCenterNode(Name=host.get('config', {}).get('instanceUuid') or alternative_name,
                           Type='ESXHost',
                           Details=host)

    def _parse_vm_host(self, vm_root):
        """
        Parse a vm host into a dict
        :param vm_root:
        :return:
        """
        # let's take what we can and return it
        summary = vm_root.summary
        attributes_from_summary = ['quickStats', 'guest', 'config', 'storage', 'runtime', 'overallStatus',
                                   'customValue', 'config']
        details = {}
        for k in attributes_from_summary:
            taken = getattr(summary, k, None)
            if taken:
                details[k] = _take_just_primitives(taken.__dict__)

        runtime = getattr(summary, 'runtime', None)
        if runtime:
            esx_host = getattr(runtime, 'host', None)
            if esx_host:
                esx_host_name = getattr(esx_host, 'name', None)
                if esx_host_name:
                    details['esx_host_name'] = esx_host_name

        config = getattr(vm_root, 'config', None)
        if config:
            hardware = getattr(config, 'hardware', None)
            if hardware:
                details['hardware'] = _take_just_primitives(hardware.__dict__)
                devices = getattr(hardware, 'device', [])
                details['hardware']['devices'] = []
                for device in devices:
                    device_raw = _take_just_primitives(device.__dict__)
                    device_info = getattr(device, 'deviceInfo', None)
                    if device_info:
                        device_raw['deviceInfo'] = _take_just_primitives(device_info.__dict__)
                    details['hardware']['devices'].append(device_raw)

        details['networking'] = list(self._parse_networking(vm_root))
        details['hardware_networking'] = list(self._parse_networking_from_hardware(vm_root))
        return details

    def _parse_vm(self, vm_root, depth=1):
        """
        Print information for a particular virtual machine or recurse into a folder
        or vApp with depth protection
        """
        self.__devices_count += 1
        if self.__devices_count % 1000 == 0:
            logger.info(f"Got {self.__devices_count} vms so far")
        maxdepth = 100
        if depth > maxdepth:
            return

        # if this is a Datacenter
        if hasattr(vm_root, 'vmFolder'):
            vm_list = vm_root.vmFolder.childEntity
            children = [self._parse_vm(c, depth + 1) for c in vm_list]
            hosts = [self._parse_host(c) for c in vm_root.hostFolder.childEntity]
            return vCenterNode(Name=vm_root.name, Type="Datacenter", Children=children + hosts)

        # if this is a group it will have children. if it does, recurse into them
        # and then return
        if hasattr(vm_root, 'childEntity'):
            vm_list = vm_root.childEntity
            children = [self._parse_vm(c, depth + 1) for c in vm_list]
            return vCenterNode(Name=vm_root.name, Type="Folder", Children=children)

        # otherwise, we're perhaps dealing with a machine

        parsed_data = self._parse_vm_host(vm_root)
        config = parsed_data.get('config')
        if not config:
            logger.error("Got a machine without a config")
            return None

        name = config.get('name')
        if not name:
            logger.error("Got a machine without a name")
            return None

        template = config.get('template')
        if template is None:
            logger.error("Got a machine without a template")
            return None

        return vCenterNode(Name=name, Type="Template" if template else "Machine", Details=parsed_data)

    @retry(stop_max_attempt_number=3, retry_on_exception=_should_retry_fetching)
    def get_all_vms(self):
        """
        Returns all details about all vms

        :return vCenterNode:
        """
        self.__devices_count = 1
        try:
            children = [self._parse_vm(x)
                        for x in
                        self._session.content.rootFolder.childEntity]
            return vCenterNode(Name="Root", Type="Root", Children=children)
        except vim.fault.NoPermission:
            # we're catching and raising so it'll be sent up to _should_retry_fetchin
            # so we will still have the logic to retry 3 times in case of a deauth
            self._connect()
            raise
