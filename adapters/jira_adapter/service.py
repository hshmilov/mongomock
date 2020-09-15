import logging

from axonius.utils.dynamic_fields import put_dynamic_field
from axonius.utils.parsing import normalize_var_name

# from axonius.fields import ListField

from axonius.smart_json_class import SmartJsonClass

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from jira_adapter.connection import JiraConnection
from jira_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')

#
# class JIRAAssetField(SmartJsonClass):
#     name = Field(str, 'Field')
#     value = Field(str, 'Value')


class JIRAAssetAssignee(SmartJsonClass):
    account_id = Field(str, 'Account ID')
    email = Field(str, 'Email')


class JIRAAssetType(SmartJsonClass):
    appkey = Field(str, 'App Key')
    origin_id = Field(str, 'Origin ID')


class JiraAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        appkey = Field(str, 'App Key')
        asset_type = Field(JIRAAssetType, 'Asset Type')
        assignee = Field(JIRAAssetAssignee, 'Assignee')
        # jira_fields = ListField(JIRAAssetField, 'Custom Fields')

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
        connection = JiraConnection(domain=client_config['domain'],
                                    verify_ssl=client_config['verify_ssl'],
                                    https_proxy=client_config.get('https_proxy'),
                                    username=client_config['username'],
                                    password=client_config['password'])
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
        The schema JiraAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Jira Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_entity_dynamic(entity_obj, entity_raw):
        for item in entity_raw.get('fields', []):
            if not isinstance(item, dict):
                continue
            key = item.get('fieldId')
            val = item.get('value')
            try:
                if not key or not val:
                    logger.debug(f'Bad item. Key "{key}" ; Value "{val}"')
                    continue
                # field_obj = JIRAAssetField(name=key, value=val)
                # entity_obj.jira_fields.append(field_obj)
                normalized_var_name = normalize_var_name(key)
                field_title = ' '.join(
                    [word.capitalize() for word in key.split(' ')])
                if entity_obj.does_field_exist(normalized_var_name):
                    # Make sure not to overwrite existing data
                    normalized_var_name = 'jira_' + normalized_var_name
                    field_title = f'JIRA Asset: {field_title}'
                put_dynamic_field(entity_obj, normalized_var_name, val, field_title)
                try:
                    if normalized_var_name == 'os':
                        entity_obj.figure_os(val)
                except Exception:
                    logger.debug(f'Failed to parse os for {entity_obj.name} from {val}')
            except Exception as e:
                logger.warning(f'Failed to add {key}:{val} to entity {entity_obj.id}: '
                               f'Got {str(e)}')
                continue

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            origin_dict = device_raw.get('origin', {})
            orig_appkey = origin_dict.get('appKey')
            orig_id = origin_dict.get('originId')
            device_id = f'{orig_appkey}/{orig_id}'
            if not (orig_id and orig_appkey):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + str(device_raw.get('label') or '')
            device.name = (device_raw.get('label') or {}).get('value')
            device.appkey = orig_appkey
            # asset type
            try:
                ass_type = device_raw.get('type', {})
                if ass_type:
                    device.asset_type = JIRAAssetType(
                        appkey=ass_type.get('appKey'),
                        origin_id=ass_type.get('originId')
                    )
            except Exception as e:
                logger.warning(f'Failed to parse asset type for {device.name}: {str(e)}')
            # assignee
            try:
                ass_dict = device_raw.get('assignee', {})
                if ass_dict:
                    device.email = ass_dict.get('email')
                    device.device_managed_by = ass_dict.get('email')
                    device.assignee = JIRAAssetAssignee(
                        account_id=ass_dict.get('accountId'),
                        email=ass_dict.get('email')
                    )
            except Exception as e:
                logger.warning(f'Failed to parse assignee for {device.name}: {str(e)}')
            # dynamic
            self._parse_entity_dynamic(device, device_raw)
            # set raw
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Jira Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
