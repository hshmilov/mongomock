import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.files import get_local_config_file
from cisco_prime_adapter.client import CiscoPrimeClient
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils import json
from axonius.clients.cisco import snmp
from axonius.clients.cisco.abstract import InstanceParser, CiscoDevice


class CiscoPrimeAdapter(AdapterBase):
    MyDeviceAdapter = CiscoDevice

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self._macs = set()

    def _get_client_id(self, client_config):
        return client_config['url']

    def _connect_client(self, client_config):
        try:
            client = CiscoPrimeClient(**client_config)
            client.connect()
            return client
        except ClientConnectionException as err:
            logger.error('Failed to connect to client {0} using config: {1}'.format(
                self._get_client_id(client_config), client_config))
            raise

    def _get_snmp_creds(self, device, session):
        creds = session.get_credentials(device)

        # TODO: we aren't handling snmpv3

        # missing snmp data
        if not json.is_valid(creds, 'snmp_read_cs', 'MANAGEMENT_ADDRESS', 'snmp_port'):
            logger.warning(f'Invalid snmp creds {creds}')
            return None, None, None

        community = creds['snmp_read_cs']
        ip, port = creds['MANAGEMENT_ADDRESS'], creds['snmp_port']

        return community, ip, port

    def get_arp_table(self, raw_device, session):
        community, ip, port = self._get_snmp_creds(raw_device, session)
        if community is not None:
            with snmp.CiscoSnmpClient(community, ip, port) as client:
                yield from client.query_all()

    def _query_devices_by_client(self, client_name, session):
        raw_devices = []
        for device in session.get_devices():
            type_, raw_device = ('cisco', device)
            yield (type_, raw_device)
            raw_devices.append(raw_device)

        for raw_device in raw_devices:
            try:
                arp_table = self.get_arp_table(raw_device, session)
                for arp_entry in arp_table:
                    yield ('neighbor', arp_entry)
            except Exception as e:
                logger.exception(f'Got exception while getting arp_table: {raw_device}')

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "url",
                    "title": "url",
                    "type": "string",
                    "description": "Cisco Prime Infrastructure url"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },

            ],
            "required": [
                "url",
                "username",
                "password",
            ],
            "type": "array"
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

        device.id = str(raw_device['summary']['deviceId'])
        device.hostname = raw_device['summary'].get('deviceName', '')
        device.device_model = raw_device['summary'].get('deviceType', '')
        device.device_model_family = raw_device['summary'].get('ProductFamily', '')
        device.reachability = raw_device['summary'].get('reachability', '')

        # TODO: Figure os dosen't support .build field detection. it very
        # ugly to use figure os, since we dosen't really figuring out the os
        # (we pass static string 'cisco')

        device.figure_os('cisco')
        device.os.build = raw_device['summary'].get('softwareVersion', '')

        # iterate the nics and add them
        for mac_name, iplist in CiscoPrimeClient.get_nics(raw_device).items():
            name, mac = mac_name
            device.add_nic(mac, ips=map(lambda ipsubnet: ipsubnet[0], iplist), subnets=map(
                lambda ipsubnet: f'{ipsubnet[0]}/{ipsubnet[1]}', iplist), name=name)

            # save mac address to prevent neighbors from adding managed cisco
            self._macs.add(mac)
        device.set_raw(raw_device)

        return device

    def _parse_raw_data(self, raw_data):
        instances = []
        for raw_device in raw_data:
            try:
                type_, raw_device = raw_device
                if type_ == 'cisco':
                    device = self.create_cisco_device(raw_device)
                    if device:
                        yield device
                elif type_ == 'neighbor':
                    instances.append(raw_device)
                else:
                    raise ValueError(f'invalid type {type_}')
            except Exception:
                logger.exception(f'Got exception while creating device: {raw_device}')
        yield from InstanceParser(instances).get_devices(self._new_device_adapter)

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
