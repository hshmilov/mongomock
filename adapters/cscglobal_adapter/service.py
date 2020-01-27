import logging

from axonius.smart_json_class import SmartJsonClass

from axonius.fields import Field, ListField

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from cscglobal_adapter.connection import CscglobalConnection
from cscglobal_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ZoneRecord(SmartJsonClass):
    lhs = Field(str, 'Left-hand side')
    rhs = Field(str, 'Right-hand side')
    ttl = Field(int, 'TTL')
    status = Field(str, 'Status')
    rec_id = Field(str, 'Record identifier')


class WeightedRecord(ZoneRecord):
    priority = Field(int, 'Priority')
    weight = Field(int, 'Weight')


class SOARecord(SmartJsonClass):
    serial = Field(int, 'SOA Serial')
    refresh = Field(int, 'SOA Refresh period')
    retry = Field(int, 'SOA Retry timeout')
    expire = Field(int, 'SOA Expire timeout')
    ttl = Field(int, 'SOA TTL')
    tech_email = Field(str, 'SOA Tech Email (raw)')
    master_host = Field(str, 'SOA Master hostname')


class ZoneInfo(SmartJsonClass):
    zone_name = Field(str, 'Zone name')
    hosting_type = Field(str, 'Zone Hosting Type')
    cnames = ListField(ZoneRecord, 'Zone CNAME records')
    txtrecords = ListField(ZoneRecord, 'Zone TXT Records')
    nsrecords = ListField(WeightedRecord, 'Zone NS Records')
    mxrecords = ListField(WeightedRecord, 'Zone MX Records')
    srv_records = ListField(WeightedRecord, 'Zone SRV Records')
    soa = Field(SOARecord, 'Zone SOA record info')


class CscglobalAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        zone_info = Field(ZoneInfo, 'Zone Information')
        a_record = Field(ZoneRecord, 'A record')
        aaaa_record = Field(ZoneRecord, 'AAAA record')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = CscglobalConnection(domain=client_config['domain'],
                                         verify_ssl=client_config['verify_ssl'],
                                         https_proxy=client_config.get('https_proxy'),
                                         bearer=client_config['bearer'],
                                         apikey=client_config['apikey'],
                                         zone_name=client_config['zone_name'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema CscglobalAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CSC API Server',
                    'default': 'https://apis.cscglobal.com',
                    'type': 'string'
                },
                {
                    'name': 'zone_name',
                    'title': 'Zone Name',
                    'type': 'string'
                },
                {
                    'name': 'bearer',
                    'title': 'User Token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'zone_name',
                'bearer',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def parse_zr(zr_dict):
        return ZoneRecord(
            lhs=zr_dict.get('lhs'),
            rhs=zr_dict.get('rhs'),
            ttl=zr_dict.get('ttl'),
            status=zr_dict.get('status'),
            rec_id=zr_dict.get('id')
        )

    @staticmethod
    def parse_wr(wr_dict):
        return WeightedRecord(
            lhs=wr_dict.get('lhs'),
            rhs=wr_dict.get('rhs'),
            ttl=wr_dict.get('ttl'),
            status=wr_dict.get('status'),
            rec_id=wr_dict.get('id'),
            priority=wr_dict.get('priority'),
            weight=wr_dict.get('weight')
        )

    @staticmethod
    def parse_zone_records(zr_dict_list):
        parsed_zrs = list()
        if not (zr_dict_list and isinstance(zr_dict_list, list)):
            return []
        for zr_raw in zr_dict_list:
            parsed_zrs.append(CscglobalAdapter.parse_zr(zr_raw))
        return parsed_zrs

    @staticmethod
    def parse_weighted_records(wr_dict_list):
        parsed_wrs = list()
        if not (wr_dict_list and isinstance(wr_dict_list, list)):
            return []
        for wr_raw in wr_dict_list:
            parsed_wrs.append(CscglobalAdapter.parse_wr(wr_raw))
        return parsed_wrs

    @staticmethod
    def parse_soa_record(soa_dict):
        if not soa_dict or not isinstance(soa_dict, dict):
            logger.warning(f'Failed to parse SOA record: {soa_dict}')
            return None
        return SOARecord(
            serial=soa_dict.get('serial'),
            refresh=soa_dict.get('refresh'),
            retry=soa_dict.get('retry'),
            expire=soa_dict.get('expire'),
            ttl=soa_dict.get('ttlZone'),
            tech_email=soa_dict.get('techEmail'),
            master_host=soa_dict.get('masterHost')
        )

    @staticmethod
    def parse_zone_info(zone_dict):
        return ZoneInfo(
            zone_name=zone_dict.get('zoneName'),
            hosting_type=zone_dict.get('hostingType'),
            cnames=CscglobalAdapter.parse_zone_records(zone_dict.get('cname')),
            txtrecords=CscglobalAdapter.parse_zone_records(zone_dict.get('txt')),
            nsrecords=CscglobalAdapter.parse_weighted_records(zone_dict.get('ns')),
            mxrecords=CscglobalAdapter.parse_weighted_records(zone_dict.get('mx')),
            srv_records=CscglobalAdapter.parse_weighted_records(zone_dict.get('srv')),
            soa=CscglobalAdapter.parse_soa_record(zone_dict.get('soa'))
        )

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if 'a' in device_raw:
                rec_type = 'a'
            elif 'aaaa' in device_raw:
                rec_type = 'aaaa'
            else:
                logger.warning(f'Bad device with no a or aaaa record: {device_raw}')
                return None
            device_record = device_raw.get(rec_type)
            zone_dict = device_raw.get('zone_info')
            device_id = device_record.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_record.get('rhs') or '')
            rhs = device_record.get('rhs')
            if rhs:
                try:
                    device.add_ips_and_macs(ips=[rhs])
                except Exception as e:
                    message = f'Failed to add ip for device {device_raw}: {str(e)}'
                    logger.exception(message)
            device.name = rhs
            # adapter specific stuff
            rec = CscglobalAdapter.parse_zr(device_record)
            if rec_type == 'a':
                device.a_record = rec
            else:
                device.aaaa_record = rec
            try:
                device.zone_info = CscglobalAdapter.parse_zone_info(zone_dict)
            except Exception as e:
                message = f'Failed to set zone_info for device {device_raw}: {str(e)}'
                logger.exception(message)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Cscglobal Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]
