import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.cisco import snmp
from axonius.clients.cisco.abstract import CiscoDevice, InstanceParser, FetchProto
from axonius.clients.cisco.console import CiscoSshClient, CiscoTelnetClient
from axonius.clients.cisco.snmp import CiscoSnmpClient
from axonius.clients.rest.connection import RESTConnection
from axonius.utils import json
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_unix_timestamp
from cisco_prime_adapter.client import CiscoPrimeClient

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoPrimeAdapter(AdapterBase):
    MyDeviceAdapter = CiscoDevice

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self._macs = set()

    def _get_client_id(self, client_config):
        return client_config['url']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('url'))

    def _connect_client(self, client_config):
        try:
            client = CiscoPrimeClient(**client_config)
            client.connect()
            return client
        except ClientConnectionException as err:
            error_message = 'Failed to connect to client {0} using config: {1}'.format(
                self._get_client_id(client_config), client_config
            )
            logger.error(error_message)
            raise

    @staticmethod
    def _get_snmp_client(creds):
        # XXX: we aren't handling snmpv3
        if not json.is_valid(creds, 'snmp_read_cs', 'MANAGEMENT_ADDRESS', 'snmp_port'):
            logger.debug(f'No snmp creds in {creds}')
            return None

        community = creds['snmp_read_cs']
        ip, port = creds['MANAGEMENT_ADDRESS'], creds['snmp_port']
        client = CiscoSnmpClient(community=community, host=ip, port=port)
        if not client.is_valid(should_log_exception=False):
            return None

        return client

    @staticmethod
    def _get_console_client(creds):
        is_valid = json.is_valid(
            creds, 'cli_port', 'MANAGEMENT_ADDRESS', 'cli_login_password', 'cli_login_username', 'cli_transport'
        )
        if not is_valid:
            logger.debug(f'No console creds in {creds}')
            return None

        password = creds['cli_login_password']
        username = creds['cli_login_username']
        ip = creds['MANAGEMENT_ADDRESS']
        port = creds['cli_port']
        transport = creds['cli_transport']

        if transport == 'telnet':
            client = CiscoTelnetClient(username=username, password=password, host=ip, port=port)
        else:
            # ssh
            client = CiscoSshClient(username=username, password=password, host=ip, port=port)

        if not client.is_valid(should_log_exception=False):
            return None

        return client

    def _get_client(self, creds):
        client = self._get_snmp_client(creds)
        if client:
            return client

        client = self._get_console_client(creds)
        if client:
            return client

        logger.warning(f'Unable to generate client {creds}')
        return None

    def __query_devices_by_client(self, session):
        arp_table = []
        tasks = []
        for type_, raw_device in session.get_devices():
            yield (type_, raw_device)

            if type_ == 'client':
                continue
            try:
                creds = session.get_credentials(raw_device)
                if not creds:
                    logger.warning(f'empty creds for {raw_device}')
                    continue
                client = self._get_client(creds)

                if not client:
                    error_message = 'unable to get client - skipping {}'.format(creds.get('MANAGEMENT_ADDRESS', ''))
                    logger.warning(error_message)
                    continue

                info_message = 'Got client for {} : {}'.format(creds.get('MANAGEMENT_ADDRESS', ''), client)
                logger.info(info_message)

                with client:
                    if isinstance(client, CiscoSnmpClient):
                        tasks += client.get_tasks()
                        continue
                    else:
                        # XXX: We can improve this code by using threadpool for each generator.
                        for entry in client.query_all():
                            yield ('neighbor', entry)
            except Exception as e:
                logger.exception(f'Got exception while creating device: {raw_device}')

        try:
            if tasks:
                for entry in snmp.run_event_loop(tasks):
                    yield ('neighbor', entry)

        except Exception as e:
            logger.exception(f'Got exception while getting async data')

    def _query_devices_by_client(self, client_name, client_data):
        session = client_data
        session.connect()
        try:
            yield from self.__query_devices_by_client(session)
        finally:
            session.disconnect()

    def _clients_schema(self):
        return {
            'items': [
                {'name': 'url', 'title': 'Cisco Prime Infrastructure Url',
                 'type': 'string', 'description': 'Cisco Prime Infrastructure url'},
                {'name': 'username', 'title': 'User Name', 'type': 'string'},
                {'name': 'password', 'title': 'Password', 'type': 'string', 'format': 'password'},
                {'name': 'wireless_vlan_exclude_list', 'title': 'Wireless VLAN Exclude List', 'type': 'string'}
            ],
            'required': ['url', 'username', 'password'],
            'type': 'array',
        }

    def create_cisco_device(self, raw_device):

        if not json.is_valid(raw_device, 'summary'):
            logger.warning(f'Invalid device {raw_device}')
            return None

        # if the device dosn't have id, it isn't really managed - ignore it
        if not json.is_valid(raw_device, {'summary': 'deviceId'}):
            logger.warning(f'unmanged device detected {raw_device}')
            return None

        # add basic info
        device = self._new_device_adapter()

        device_model = ''
        device_serial = ''

        udi_detail = raw_device.get('udiDetails', {}).get('udiDetail', [])
        if udi_detail:
            device_model = udi_detail[0].get('modelNr', '')
            device_serial = udi_detail[0].get('udiSerialNr', '')
            if device_serial == 'XXXXXXXXXXX':
                device_serial = ''
                device_model = ''

        device.id = str(raw_device['summary']['deviceId'])
        device.hostname = raw_device['summary'].get('deviceName', '')
        device.device_type = raw_device['summary'].get('deviceType', '')
        device.device_model = device_model
        device.device_serial = device_serial
        device.device_model_family = raw_device['summary'].get('ProductFamily', '')
        device.reachability = raw_device['summary'].get('reachability', '')
        device.fetch_proto = FetchProto.PRIME_CLIENT.name

        ip_address = raw_device['summary'].get('ipAddress', '')
        try:
            device.add_nic(None, [ip_address])
        except Exception:
            logger.exception(f'Problem adding basic nic {raw_device}')
        # XXX: Figure os dosen't support .build field detection. it very
        # ugly to use figure os, since we dosen't really figuring out the os
        # (we pass static string 'cisco')

        device.figure_os('cisco')
        device.os.build = raw_device['summary'].get('softwareVersion', '')

        # iterate the nics and add them
        for mac_name, iplist in CiscoPrimeClient.get_nics(raw_device).items():
            name, mac = mac_name
            device.add_nic(
                mac,
                ips=map(lambda ipsubnet: ipsubnet[0], iplist),
                subnets=map(lambda ipsubnet: f'{ipsubnet[0]}/{ipsubnet[1]}', iplist),
                name=name,
            )

            # save mac address to prevent neighbors from adding managed cisco
            self._macs.add(mac)
        device.set_raw(raw_device)

        return device

    def create_prime_client_device(self, raw_device):
        device = self._new_device_adapter()
        device_id = raw_device.get('@id')
        if device_id:
            device_id = str(device_id)
        device_uuid = raw_device.get('@uuid')
        if not device_id and not device_uuid:
            logger.warning(f'Bad device with no ID {raw_device}')
            return None
        mac_address = raw_device.get('macAddress')
        device.id = '_'.join([item or '' for item in [device_id, device_uuid, mac_address]])
        try:
            ip_address = raw_device.get('ipAddress') or {}
            if isinstance(ip_address, dict):
                ip_address = ip_address.get('address')
            else:
                ip_address = None
            ips = [ip_address] if ip_address else None
            device.add_nic(mac_address, ips)
            device.wireless_vlan = raw_device.get('vlanName') or raw_device.get('vlan')
        except Exception:
            logger.exception(f'Problem getting NIC for {raw_device}')
        device.hostname = raw_device.get('hostname')
        try:
            device.ad_domainName = raw_device.get('adDomainName')
            ap_ip_address = raw_device.get('apIpAddress')
            if isinstance(ap_ip_address, dict):
                device.ap_ip_address = ap_ip_address.get('address')
            device.ap_mac_address = raw_device.get('apMacAddress')
            device.ap_name = raw_device.get('apName')
            device.auth_algo = raw_device.get('authenticationAlgorithm')
        except Exception:
            logger.exception(f'Problem getting AP info for {raw_device}')
        device.nac_state = raw_device.get('nacState')
        try:
            device.last_used_users = (raw_device.get('userName') or '').split(',')
        except Exception:
            logger.exception(f'Problem getting users for {raw_device}')
        device.association_time = parse_unix_timestamp(raw_device.get('associationTime'))
        device.fetch_proto = FetchProto.PRIME_WIFI_CLIENT.name
        device.set_raw(raw_device)
        return device

    def _parse_raw_data(self, devices_raw_data):
        instances = []
        for raw_device in devices_raw_data:
            try:
                type_, raw_device = raw_device
                if type_ == 'cisco':
                    device = self.create_cisco_device(raw_device)
                    device.adapter_properties = [AdapterProperty.Network.name, AdapterProperty.Manager.name]
                    if device:
                        yield device
                elif type_ == 'neighbor':
                    instances.append(raw_device)
                elif type_ == 'client':
                    device = self.create_prime_client_device(raw_device)
                    if device:
                        device.adapter_properties = [AdapterProperty.Network.name]
                        yield device
                else:
                    raise ValueError(f'invalid type {type_}')
            except Exception:
                logger.exception(f'Got exception while creating device: {raw_device}')
        yield from InstanceParser(instances).get_devices(self._new_device_adapter)

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
