import logging
import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import normalize_var_name
from snipeit_adapter.connection import SnipeitConnection
from snipeit_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SnipeitAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        asset_tag = Field(str, 'Asset Tag')
        status_label = Field(str, 'Status Label')
        category = Field(str, 'Category')
        assigned_to = Field(str, 'Assigned To')
        company = Field(str, 'Company')
        created_at = Field(datetime.datetime, 'Created At')
        last_checkout = Field(datetime.datetime, 'Last Checkout')
        location = Field(str, 'Location')
        purchase_date = Field(datetime.datetime, 'Purchase Date')
        updated_at = Field(datetime.datetime, 'Updated At')
        warranty_expires = Field(datetime.datetime, 'Warranty Expires')
        supplier = Field(str, 'Supplier')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with SnipeitConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                   apikey=client_config['apikey'],
                                   ) as connection:
                return connection
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
        The schema SnipeitAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Snipeit Domain',
                    'type': 'string'
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
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,R0915
    def _parse_raw_data(self, devices_raw_data):
        # pylint: disable=R1702
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                # Check for None and not "if not device_id" because we want to allow 0 as a value
                if device_id is None:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('name') or '') + \
                    '_' + (device_raw.get('serial') or '')
                name = device_raw.get('name')
                if name:
                    device.name = name
                device_serial = device_raw.get('serial')
                if device_serial:
                    device.device_serial = device_serial
                device.asset_tag = device_raw.get('asset_tag')
                try:
                    device.device_model = (device_raw.get('model') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting model for {device_raw}')
                try:
                    device.status_label = (device_raw.get('status_label') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting status label for {device_raw}')
                try:
                    device.category = (device_raw.get('category') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting category for {device_raw}')
                try:
                    device.device_manufacturer = (device_raw.get('manufacturer') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting manufacturer for {device_raw}')
                try:
                    device.assigned_to = (device_raw.get('assigned_to') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting assigned to')
                try:
                    device.company = (device_raw.get('company') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting company for {device_raw}')
                try:
                    device.supplier = (device_raw.get('supplier') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting supplier for {device_raw}')
                try:
                    device.location = (device_raw.get('location') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting location for {device_raw}')
                try:
                    device.created_at = parse_date((device_raw.get('created_at') or {}).get('datetime'))
                except Exception:
                    logger.exception(f'Problem getting created at {device_raw}')
                try:
                    device.last_checkout = parse_date((device_raw.get('last_checkout') or {}).get('datetime'))
                except Exception:
                    logger.exception(f'Problem getting last_checkout {device_raw}')
                try:
                    device.purchase_date = parse_date((device_raw.get('purchase_date') or {}).get('datetime'))
                except Exception:
                    logger.exception(f'Problem getting purchase_date {device_raw}')
                try:
                    device.updated_at = parse_date((device_raw.get('updated_at') or {}).get('datetime'))
                except Exception:
                    logger.exception(f'Problem getting updated_at {device_raw}')
                try:
                    device.warranty_expires = parse_date((device_raw.get('warranty_expires') or {}).get('datetime'))
                except Exception:
                    logger.exception(f'Problem getting warranty_expires {device_raw}')
                try:
                    custom_fields = device_raw.get('custom_fields')
                    if isinstance(custom_fields, dict):
                        for custom_key in custom_fields.keys():
                            try:
                                new_key = 'snipe_it_' + normalize_var_name(custom_key)
                                if not device.does_field_exist(new_key):
                                    cn_capitalized = ' '.join([word.capitalize() for word in custom_key.split(' ')])
                                    device.declare_new_field(new_key, Field(str, f'SnipeIT {cn_capitalized}'))

                                device[new_key] = custom_fields[custom_key]['value']
                            except Exception:
                                logger.exception(f'Problem adding key {custom_key}')
                except Exception:
                    logger.exception(f'Problem getting custom fields {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Snipeit Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
