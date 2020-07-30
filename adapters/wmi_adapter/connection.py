import logging

from typing import List, Iterator, Optional


from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.wmi_query.query import execute_shell, WmiResults
from axonius.utils.ips import parse_ips_list, port_scan
from axonius.clients.wmi_query import query, consts
from wmi_adapter.consts import DEFAULT_POOL_SIZE
from wmi_adapter.parsers.basic_computer_info import GetBasicComputerInfo
from wmi_adapter.parsers.connected_hardware import GetConnectedHardware
from wmi_adapter.parsers.installed_softwares import GetInstalledSoftwares
from wmi_adapter.parsers.reg_file_subplugin import CheckReg
from wmi_adapter.parsers.user_logons import GetUserLogons

logger = logging.getLogger(f'axonius.{__name__}')


class WmiConnection:
    """
    Wmi connection client
    This class should handle wmi scans and wmi query/execution.
    Notes:
        This class is using a python2.7 Avidor's modified Impacket for wmi query/exec.
        Its ugly to open a python2.7 subprocess but for now its the best option.
    """

    def __init__(self, targets, username, password, dns_servers, python27_path, wmi_smb_path,
                 registry_keys=None, hostname_for_validation=None, pool_size=DEFAULT_POOL_SIZE):
        """
        Init WmiConnection class
        :param targets: targets to scan, can be a list of targets or a single one
        :param username: username for RPC auth
        :param password: password for RPC auth
        :param dns_server: additional dns server for resolving target name
        :param python27_path: python27 path on axonius system
        :param wmi_smb_path: wmi_smb_path python path for axonius system
        :param hostname_for_validation: hostname to validate the target (by code execution)
        :param pool_size: max parallel threads for running wmi
        """
        self._targets = targets
        self._username = username
        self._password = password
        self._dns_servers = [x.strip() for x in dns_servers.split(',') if x] if dns_servers else []
        self._python27_path = python27_path
        self._wmi_smb_path = wmi_smb_path
        self._registry_keys = registry_keys
        self._hostname_for_validation = hostname_for_validation
        self.pool_size = pool_size

    def __enter__(self):
        return self

    # pylint: disable=C0103
    def __exit__(self, _type, value, tb):
        pass

    # pylint: disable=W0102
    @staticmethod
    def test_reachability(hostname: str, dns_servers=None, ports=consts.WMI_SCAN_PORTS) -> bool:
        """
        There is not proper way for testing wmi reachability.
        the best option is to scan for SMB and RPC ports.
        :param hostname: hostname to check
        :param dns_servers: dns servers for resolving the hostname (in addition to the default one)
        :param ports: ports to be checked
        :return: True if all the ports are open, otherwise false.
        Notes: If hostname is more than one host, we wont check it.
        """
        # we assume that hostname is more than one host, we wont check it for now
        if ',' in hostname or '/' in hostname:
            return True
        dns_servers = [x.strip() for x in dns_servers.split(',') if x] if dns_servers else []
        try:
            # Get open ports for the hostname
            results = list(port_scan(hostname, ports, dns_servers=dns_servers))
            if not results:
                return False
            # Check if all the WMI_SCAN_PORTS are open on this hostname
            if set(consts.WMI_SCAN_PORTS).issubset(set(results[0].open_ports)):
                return True
        except Exception:
            logger.exception(f'Error testing reachability for {hostname}')
        return False

    def _connect(self):
        if not self._username or not self._password:
            raise ClientConnectionException('No username or password')

    def exec_cmd(self, commands: List[str], extra_files: Optional[dict] = None) -> Iterator[WmiResults]:
        """
        Exec code on devices.
        :param commands: commands to be executed
        :param extra_files: files to be uploaded before the command execution.
        :return: wmi exec response object
        Notes: each object of the iterator is another device response
        """
        resolved_hosts = self.resolve_hosts(self._targets, self._dns_servers, self._hostname_for_validation)
        if not resolved_hosts:
            logger.error('No resolvable hosts')
            return
        try:
            logger.debug(f'Executing cmd on {resolved_hosts}')
            targets_outputs = execute_shell(devices_ips=resolved_hosts,
                                            python_27_path=self._python27_path,
                                            wmi_smb_path=self._wmi_smb_path,
                                            username=self._username,
                                            password=self._password,
                                            shell_commands={'Windows': commands},
                                            extra_files=extra_files
                                            )
            yield from targets_outputs
        except Exception:
            logger.exception('Error executing shell command')
            # yield none for keeping the results order.
            yield None

    @staticmethod
    def resolve_hosts(hosts, dns_servers, hostname_for_validation=None) -> list:
        """
        Resolve the given hosts.
        :param hosts: Hosts to resolve
        Hosts can be a string of comma separated ips, hostnames or domains.
        for example: '192.168.1.1, google.com, 10.0.0.0/24'
        :param dns_servers: dns server to use in addition to the default one
        :param hostname_for_validation: hostname to validate the target (by code execution)
        :return: list of resolved hosts ips
        """
        resolved_hosts = []
        try:
            resolved_hosts = [x for x in
                              parse_ips_list(hosts, resolve=True, dns_servers=dns_servers)
                              if x]

            # If there is more than 1 hosts to scan, we do not validate hostname.
            # (there is no reason for hosts validation on adapter's data)
            if len(resolved_hosts) > 1 or not hostname_for_validation:
                resolved_hosts = [(ip, None) for ip in resolved_hosts]
            else:
                resolved_hosts = [(ip, hostname_for_validation) for ip in resolved_hosts]
        except Exception:
            logger.exception('Error resolving hostnames')
            return []
        return resolved_hosts

    def get_device_list(self):
        resolved_hosts = self.resolve_hosts(self._targets, self._dns_servers, self._hostname_for_validation)
        if not resolved_hosts:
            logger.error('Bad hostnames/ips')
            return

        wmi_smb_commands = []
        # Initialize all of our subplugins
        subplugins_objects = [GetUserLogons, GetInstalledSoftwares, GetBasicComputerInfo, GetConnectedHardware]
        subplugins_list = [con(logger) for con in subplugins_objects]
        if self._registry_keys:
            subplugins_list.append(CheckReg(logger, reg_check_exists=self._registry_keys))
        for subplugin in subplugins_list:
            try:
                wmi_smb_commands.extend(subplugin.get_wmi_smb_commands())
            except Exception:
                logger.exception(f'Error getting {subplugin.__class__.__name__} commands')
        try:
            logger.debug(f'Running wmi scan on {resolved_hosts}')
            queries_response = query.run_wmi_smb_on_devices(self._python27_path,
                                                            self._wmi_smb_path,
                                                            self._username, self._password,
                                                            wmi_smb_commands,
                                                            resolved_hosts,
                                                            max_workers=self.pool_size)
            for dev in queries_response:
                yield subplugins_list, dev
        except Exception:
            logger.exception('Error running wmi commands')
