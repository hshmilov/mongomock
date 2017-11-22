"""
vCenterApi.py: A wrapper for vCenter SOAP services
"""

__author__ = "Mark Segal"

from pyVim import connect
from pyVmomi.VmomiSupport import Enum as pyVmomiEnum
from retrying import retry
from datetime import datetime
from namedlist import namedlist
from pyVmomi import vim

vCenterNode = namedlist(
    'vCenterNode', ['Name', 'Type', ('Children', []), ('Details', None)])


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
    return vCenterNode(folder.Name, folder.Type, [rawify_vcenter_data(child) for child in folder.Children],
                       folder.Details)._asdict()


def _should_retry_fetching(exception):
    return isinstance(exception, vim.fault.NoPermission)


class vCenterApi():
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
        guest_net = vm.guest.net
        if guest_net is None:
            return iter([])
        for network in guest_net:
            if network is None:
                continue
            primitives = _take_just_primitives(network.__dict__)
            if network.ipConfig is not None:
                primitives['ipAddresses'] = [_take_just_primitives(addr.__dict__) for addr in
                                             network.ipConfig.ipAddress]
            yield primitives

    def _parse_vm(self, vm, depth=1):
        """
        Print information for a particular virtual machine or recurse into a folder
        or vApp with depth protection
        """
        maxdepth = 100

        # if this is a group it will have children. if it does, recurse into them
        # and then return
        if hasattr(vm, 'childEntity'):
            if depth > maxdepth:
                return
            vm_list = vm.childEntity
            children = [self._parse_vm(c, depth + 1) for c in vm_list]
            return vCenterNode(Name=vm.name, Type="Folder", Children=children)

        # otherwise, we're dealing with a machine
        # let's take what we can and return it
        summary = vm.summary
        attributes_from_summary = ['config', 'quickStats', 'guest', 'config', 'storage', 'runtime', 'overallStatus',
                                   'customValue']
        details = {k: _take_just_primitives(summary.__getattribute__(
            k).__dict__) for k in attributes_from_summary}
        details['networking'] = list(self._parse_networking(vm))

        return vCenterNode(Name=summary.config.name, Type="Machine", Details=details)

    @retry(stop_max_attempt_number=3, retry_on_exception=_should_retry_fetching)
    def get_all_vms(self):
        """
        Returns all details about all vms

        :return vCenterNode:
        """
        try:
            children = [vCenterNode(Name=dc.name, Type="Datacenter",
                                    Children=[self._parse_vm(vm) for vm in dc.vmFolder.childEntity])
                        for dc in
                        self._session.content.rootFolder.childEntity

                        # an existance of 'vmFolder' is a good indicator that the node is a 'Datacenter'
                        if hasattr(dc, 'vmFolder')]
            return vCenterNode(Name="Datacenters", Type="Folder", Children=children)
        except vim.fault.NoPermission:
            # we're catching and raising so it'll be sent up to _should_retry_fetchin
            # so we will still have the logic to retry 3 times in case of a deauth
            self._connect()
            raise
