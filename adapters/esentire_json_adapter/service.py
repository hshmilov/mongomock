import logging

from axonius.consts import remote_file_consts
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.datetime import parse_date
from axonius.utils.json import from_json
from axonius.utils.parsing import is_domain_valid
from axonius.utils.files import get_local_config_file
from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.remote_file_utils import load_remote_data, test_file_reachability
from esentire_json_adapter.client_id import get_client_id
from esentire_json_adapter.structures import EsentireJsonDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class EsentireJsonAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(EsentireJsonDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return test_file_reachability(client_config)

    def _connect_client(self, client_config):
        try:
            file_name, file_data = load_remote_data(client_config)

            return file_name, from_json(file_data)
        except Exception as e:
            message = f'Error connecting to esentire json: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        file_name, json_data = client_data
        return json_data

    @staticmethod
    def _clients_schema():
        """
        The schema EsentireJsonAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                *remote_file_consts.FILE_CLIENTS_SCHEMA
            ],
            'required': [
                *remote_file_consts.FILE_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_esentire_json_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.sensor = device_raw.get('sensor')
            device.network_tap = device_raw.get('network_tap')
            total_traffic_in_bytes = device_raw.get('total_traffic_in_bytes')
            if isinstance(total_traffic_in_bytes, (str, int)):
                device.total_traffic_in_bytes = int(total_traffic_in_bytes)
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            ip = device_raw.get('ip')
            if not (ip and isinstance(ip, str)):
                logger.warning(f'Device with no IP for {device_raw}')
                return None
            hostname = device_raw.get('hostname')
            device.id = f'{ip}_{hostname or ""}'

            # example: hostname = "[\"REDACTED\"]"
            if isinstance(hostname, str) and ('[' in hostname) and (']' in hostname):
                try:
                    hostname = from_json(hostname)
                except Exception:
                    logger.warning(f'Failed parsing json hostname: {hostname}')

            if isinstance(hostname, list) and hostname:
                # save the original list in a proprietary field
                device.parsed_hostnames = hostname
                hostname = hostname[0]

            device.hostname = hostname

            if (isinstance(hostname, str) and (hostname.count('.') > 2)):
                domain = '.'.join(hostname.split('.')[1:])
                if is_domain_valid(domain):
                    device.domain = domain

            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.add_ips_and_macs(ips=[ip])

            self._fill_esentire_json_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching EsentireJson Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching EsentireJson Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
