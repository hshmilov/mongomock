import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.consts import remote_file_consts
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import make_dict_from_csv
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from axonius.utils.remote_file_utils import load_remote_data, test_file_reachability
from ud_csv_adapter.client_id import get_client_id
from ud_csv_adapter.structures import UdCsvDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class UdCsvAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(UdCsvDeviceInstance):
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
            try:
                make_dict_from_csv(file_data)
            except Exception as e:
                raise ClientConnectionException(f'Failed to load csv data: {str(e)}')
            return file_name, file_data
        except Exception as err:
            logger.exception(f'Error connecting to sqlite database')
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    @staticmethod
    def _clients_schema():
        """
        The schema UdCsvAdapter expects from configs

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

    # pylint:disable=arguments-differ
    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        file_name, csv_data = client_data
        return make_dict_from_csv(csv_data)

    @staticmethod
    def _fill_ud_csv_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.region = device_raw.get('REGION')
            device.it_customer = device_raw.get('IT_CUSTOMER')
            device.division_name = device_raw.get('DIVISIONNAME')
            device.country_name = device_raw.get('CountryName')
            device.cmdb_id = device_raw.get('cmdb_id')
            device.vm_status = device_raw.get('VM Status')
            device.device_type = device_raw.get('DeviceType')
            device.comment = device_raw.get('COMMENT')
            device.contact_person = device_raw.get('CONTACT_PERSON')
            device.bucategory = device_raw.get('BUCATEGORY')
            device.team_leader = device_raw.get('CC_TEAM_LEADER')
            if device_raw.get('ALL_IPS'):
                device.all_ips = device_raw.get('ALL_IPS').split(',')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('SERVERNAME')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('cmdb_id') or '')
            device.hostname = device_raw.get('SERVERNAME')
            device.device_serial = device_raw.get('Host Serial Number')
            device.add_nic(ips=[device_raw.get('PRIMARY_IP')])
            device.last_seen = parse_date(device_raw.get('Last Access Date'))
            device.device_model = device_raw.get('UD Node Model')
            device.email = device_raw.get('CC_PRIMARY_MAIL')
            device.domain = device_raw.get('Server Domain')
            device.figure_os((device_raw.get('OS') or '') + ' ' +
                             (device_raw.get('OS Category') or '') + ' ' + (device_raw.get('OS Version') or ''))
            self._fill_ud_csv_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching UdCsv Device for {device_raw}')
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
                logger.exception(f'Problem with fetching UdCsv Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
