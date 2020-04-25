import logging
import numbers
from threading import Lock

import cachetools

from axonius.utils.threading import singlethreaded

logger = logging.getLogger(f'axonius.{__name__}')
from pyVmomi.VmomiSupport import Enum as pyVmomiEnum
from retrying import retry
from datetime import datetime
from namedlist import namedlist

import requests
from com.vmware.cis.tagging_client import Tag, TagAssociation, TagModel
from com.vmware.cis_client import Session
from com.vmware.vapi.std_client import DynamicID
from pyVim import connect
from pyVmomi import vim
from vmware.vapi.lib.connect import get_requests_connector
from vmware.vapi.security.session import create_session_security_context
from vmware.vapi.security.user_password import create_user_password_security_context
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory


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


def _getattr_permission_safely(obj, attr_name, default=None):
    try:
        value = getattr(obj, attr_name, default)
        # We want to perform 'or default' additionally but '0' is a valid integer value, so don't do it for numbers.
        # See: https://docs.python.org/3/library/stdtypes.html#truth-value-testing
        #  +   https://stackoverflow.com/a/4187266
        if not isinstance(value, numbers.Number):
            value = value or default
        return value
    except vim.fault.NoPermission:
        logger.warning(f'Object {obj} had no permissions for attribute "{attr_name}", returning {default}.')
        return default


class vCenterApi(object):
    """ vCenterApi.py: A wrapper for vCenter SOAP services """

    def __init__(self, host, user, password, verify_ssl=False, restful_api_url: str = None):
        """
        Ctor
        :param str host: ip or dns of the vcenter server
        :param str user: your username
        :param str password: your password
        :param bool verify_ssl: should we verify SSL or not
        :param restful_api_url: If present, will try to fetch additional data from this API as well
        :raise See pyVim documentation for connect
        """
        self._verify_ssl = verify_ssl
        self._host = host
        self._user = user
        self._password = password
        self.__restful_api_url = restful_api_url
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

        # service that translate Tag IDs into their information
        self.__tag_svc = None

        # service that allows us to figure out associated tags
        self.__tag_association = None

        if self.__restful_api_url:
            try:
                self.__get_tag_svc()
            except Exception:
                logger.warning('Failed setting up vshpere automation sdk for taggins', exc_info=True)
                self.__tag_association = None
                self.__tag_svc = None

    def __get_tag_svc(self):
        """
        Code is adapted from
        https://github.com/vmware/vsphere-automation-sdk-python/tree/master/samples/vsphere/tagging
        """
        session = requests.Session()
        session.verify = self._verify_ssl

        connector = get_requests_connector(session=session, url=self.__restful_api_url)
        stub_config = StubConfigurationFactory.new_std_configuration(connector)

        # Pass user credentials (user/password) in the security context to authenticate.
        # login to vAPI endpoint
        user_password_security_context = create_user_password_security_context(self._user, self._password)
        stub_config.connector.set_security_context(user_password_security_context)

        # Create the stub for the session service and login by creating a session.
        session_svc = Session(stub_config)
        session_id = session_svc.create()

        # Successful authentication.  Store the session identifier in the security
        # context of the stub and use that for all subsequent remote requests
        session_security_context = create_session_security_context(session_id)
        stub_config.connector.set_security_context(session_security_context)
        self.__tag_svc = Tag(stub_config)
        self.__tag_association = TagAssociation(stub_config)
        logger.info('Tagging fetching enabled')

    def _parse_networking(self, vm):
        """
        Parses networking from vm state
        :return: iter(dict)
        """
        guest = _getattr_permission_safely(vm, 'guest', None)
        if not guest:
            return
        guest_net = guest.net
        if guest_net is None:
            return
        for network in guest_net:
            if network is None:
                continue
            primitives = _take_just_primitives(network.__dict__)
            if network.ipConfig is not None:
                primitives['ipAddresses'] = [_take_just_primitives(addr.__dict__) for addr in
                                             network.ipConfig.ipAddress]
            yield primitives

    def _parse_networking_from_hardware(self, vm_root):
        config = _getattr_permission_safely(vm_root, 'config', None)
        if not config:
            return
        network = _getattr_permission_safely(config, 'network', None)
        if not network:
            return
        vnic = _getattr_permission_safely(network, 'vnic', None)
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

        details = None
        summary = _getattr_permission_safely(host, 'summary', None)
        if summary:
            values_to_take = ['totalCpu', 'totalMemory', 'numCpuCores', 'numCpuThreads', 'effectiveCpu', 'effectiveMemory',
                              'numHosts', 'numEffectiveHosts', 'overallStatus']
            try:
                details = {k: _getattr_permission_safely(summary, k, None) for k in values_to_take}
            except Exception:
                logger.warning(f'Problem getting details', exc_info=True)
        try:
            parsed_hosts = [self._parse_vm_host(x) for x in _getattr_permission_safely(host, 'host', [])]
        except Exception:
            logger.warning(f'Problem getting hosts', exc_info=True)
            parsed_hosts = []

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

    @singlethreaded()
    @cachetools.cached(cachetools.TTLCache(maxsize=5000, ttl=120), lock=Lock())
    def __get_tagdata_from_tagid(self, tag_id: str) -> TagModel:
        """
        Uses tag_svc to get a TagModel form the tag_id given
        :param tag_id: The tag ID,
        something like this 'urn:vmomi:InventoryServiceTag:23372443-84b1-4c4f-b323-5008a25da0fc:GLOBAL'
        """
        res = self.__tag_svc.get(tag_id)
        return res.name, res.description

    def __get_all_tags(self, vm):
        """
        Uses self.__tag_svc to get tags of a given VM
        :param vm: pyVmomi.VmomiSupport.vim.VirtualMachine
        """
        if not self.__tag_association or not self.__tag_svc:
            return None

        try:
            dynamic_id = DynamicID(type=vm._wsdlName, id=vm._GetMoId())
            all_tags = self.__tag_association.list_attached_tags(dynamic_id)
            return [self.__get_tagdata_from_tagid(tag) for tag in all_tags]
        except Exception:
            logger.warning(f'Error on tags fetching {vm} {vm._wsdlName} {vm._GetMoId()}', exc_info=True)
            return None

    def _parse_vm_host(self, vm_root):
        """
        Parse a vm host into a dict
        :param vm_root:
        :return:
        """
        # let's take what we can and return it
        details = {}
        summary = _getattr_permission_safely(vm_root, 'summary', None)
        if summary:
            attributes_from_summary = ['quickStats', 'guest', 'config', 'storage', 'runtime', 'overallStatus',
                                       'customValue']
            for k in attributes_from_summary:
                taken = _getattr_permission_safely(summary, k, None)
                if taken:
                    details[k] = _take_just_primitives(taken.__dict__)

            runtime = _getattr_permission_safely(summary, 'runtime', None)
            if runtime:
                esx_host = _getattr_permission_safely(runtime, 'host', None)
                if esx_host:
                    esx_host_name = _getattr_permission_safely(esx_host, 'name', None)
                    if esx_host_name:
                        details['esx_host_name'] = esx_host_name

            summary_config = _getattr_permission_safely(summary, 'config', None)
            if summary_config:
                product = _getattr_permission_safely(summary_config, 'product', None)
                if product:
                    details.setdefault('config', {})['product'] = _take_just_primitives(product.__dict__)

        config = _getattr_permission_safely(vm_root, 'config', None)
        if config:
            hardware = _getattr_permission_safely(config, 'hardware', None)
            if hardware:
                details['hardware'] = _take_just_primitives(hardware.__dict__)
                devices = _getattr_permission_safely(hardware, 'device', [])
                details['hardware']['devices'] = []
                for device in devices:
                    device_raw = _take_just_primitives(device.__dict__)
                    device_info = _getattr_permission_safely(device, 'deviceInfo', None)
                    if device_info:
                        device_raw['deviceInfo'] = _take_just_primitives(device_info.__dict__)
                    details['hardware']['devices'].append(device_raw)

        hardware = _getattr_permission_safely(vm_root, 'hardware', None)
        if hardware:
            bios_info = _getattr_permission_safely(hardware, 'biosInfo', None)
            if bios_info:
                details['esx_bios_info'] = _take_just_primitives(bios_info.__dict__)

            system_info = _getattr_permission_safely(hardware, 'systemInfo', None)
            if system_info:
                details['esx_system_info'] = _take_just_primitives(system_info.__dict__)
                other_identifying_info_list = _getattr_permission_safely(system_info, 'otherIdentifyingInfo', [])
                if other_identifying_info_list:
                    # https://www.vmware.com/support/developer/converter-sdk/conv55_apireference/vim.host.SystemIdentificationInfo.html
                    other_info = details['esx_system_info']['otherIdentifyingInfo'] = []
                    for other_identifying_info in other_identifying_info_list:
                        id_type = _getattr_permission_safely(other_identifying_info, 'identifierType', None)
                        if not id_type:
                            continue
                        id_value = _getattr_permission_safely(other_identifying_info, 'identifierValue', None)
                        other_info.append({'key': _getattr_permission_safely(id_type, 'key', None),
                                           'value': id_value})

        details['networking'] = list(self._parse_networking(vm_root))
        details['hardware_networking'] = list(self._parse_networking_from_hardware(vm_root))
        details['tags'] = self.__get_all_tags(vm_root)
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
        try:
            # if this is a Datacenter
            if hasattr(vm_root, 'vmFolder'):
                vm_list = vm_root.vmFolder.childEntity
                children = [self._parse_vm(c, depth + 1) for c in vm_list]
                hosts = [self._parse_host(c) for c in vm_root.hostFolder.childEntity]
                return vCenterNode(Name=vm_root.name, Type="Datacenter", Children=children + hosts)
        except Exception:
            logger.warning('Problem with VmFolder', exc_info=True)
            return None

        try:
            # if this is a group it will have children. if it does, recurse into them
            # and then return
            if hasattr(vm_root, 'childEntity'):
                vm_list = vm_root.childEntity
                children = [self._parse_vm(c, depth + 1) for c in vm_list]
                return vCenterNode(Name=vm_root.name, Type="Folder", Children=children)
        except Exception:
            logger.warning('Problem getting child', exc_info=True)
            return None
        try:
            # otherwise, we're perhaps dealing with a machine
            parsed_data = self._parse_vm_host(vm_root)
            config = parsed_data.get('config')
            if not config:
                logger.warning("Got a machine without a config", exc_info=True)
                return None
        except Exception:
            logger.warning('Problem parting machine', exc_info=True)
            return None

        name = config.get('name')
        if not name:
            logger.warning("Got a machine without a name", exc_info=True)
            return None

        template = config.get('template')
        if template is None:
            logger.warning("Got a machine without a template", exc_info=True)
            return None
        try:
            vcenter_node = vCenterNode(Name=name, Type="Template" if template else "Machine", Details=parsed_data)
            return vcenter_node
        except Exception:
            logger.warning('Problem getting node', exc_info=True)
            return None

    @retry(stop_max_attempt_number=3, retry_on_exception=_should_retry_fetching)
    def get_all_vms(self):
        """
        Returns all details about all vms

        :return vCenterNode:
        """
        self.__devices_count = 1
        try:
            children = []
            for vm_to_parse in self._session.content.rootFolder.childEntity:
                try:
                    children.append(self._parse_vm(vm_to_parse))
                except Exception:
                    logger.warning(f'Problem parsing vm to parse: {str(vm_to_parse)}', exc_info=True)
            return vCenterNode(Name="Root", Type="Root", Children=children)
        except vim.fault.NoPermission:
            # we're catching and raising so it'll be sent up to _should_retry_fetchin
            # so we will still have the logic to retry 3 times in case of a deauth
            self._connect()
            raise
