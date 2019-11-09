# pylint: disable=import-error
import json
from enum import Enum
from datetime import datetime
import contextlib
import warnings
import logging
import requests
from urllib3.exceptions import InsecureRequestWarning
import pytz
# pylint: disable=import-error
from gql import Client, gql
# pylint: disable=import-error
from gql.transport.requests import RequestsHTTPTransport

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.smart_json_class import SmartJsonClass
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from preempt_adapter.client_id import get_client_id
from preempt_adapter.consts import QUERY_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=invalid-name
old_merge_environment_settings = requests.Session.merge_environment_settings


@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except Exception:
                pass


# pylint: disable=unnecessary-lambda
def default_json_encode(obj):
    """
    Converts the given UTC datetimes in the object to theirs string representation in ISO format
    """
    if isinstance(obj, datetime):
        obj = obj.replace(tzinfo=pytz.UTC)
        return obj.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, set)):
        return map(lambda d1: default_json_encode(d1), obj)
    if isinstance(obj, dict):
        return {key: default_json_encode(value) for key, value in obj.items()}
    return obj


class RiskFactor(SmartJsonClass):
    factor_type = Field(str, 'Factor Type')
    factor_severiry = Field(str, 'Factor Severity')


class PreemptAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        risk_score = Field(float, 'Risk score')
        is_server = Field(bool, 'Is Server')
        risk_score_severity = Field(str, 'Risk Score Severity')
        risk_factors = ListField(RiskFactor, 'Risk Factors')
        owner = Field(str, 'Owner')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def execute_query(gql_client, query, variables=None):
        try:
            if variables:
                variables = dict((k, v) for k, v in variables.items() if v is not None)
                variables = json.dumps(variables, default=default_json_encode)
            with no_ssl_verification():
                return gql_client.execute(document=query, variable_values=variables)

        except Exception as e:
            logger.exception(f'Failed executing query with varialbes: {str(variables)}')
            raise

    # pylint: disable=stop-iteration-return
    def execute_paginated_query(self, gql_client, query, variables):
        end_cursor = variables.get('after', None)
        should_continue = True
        while should_continue:
            variables['after'] = end_cursor
            gql_connection = next(iter(self.execute_query(gql_client, query, variables).values()))
            yield from gql_connection['nodes']
            page_info = gql_connection.get('pageInfo')
            should_continue = page_info['hasNextPage']
            if should_continue:
                end_cursor = page_info['endCursor']

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        gql_client = client_data
        query = gql(QUERY_DEVICES)

        variables = {
            'limit': 1000,
            'sortOrder': 'ASCENDING',
            'after': None
        }
        return self.execute_paginated_query(gql_client, query, variables)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            domain = client_config['domain']
            url = f'{domain}/api/public/graphql'
            apikey = client_config['apikey']
            gql_client = Client(
                retries=3,
                transport=RequestsHTTPTransport(url=url,
                                                timeout=(60, 600),
                                                headers={'Authorization': f'Bearer {apikey}'}))
            query = gql(QUERY_DEVICES)
            variables = {
                'limit': 10,
                'sortOrder': 'ASCENDING',
                'after': None
            }
            next(iter(self.execute_query(gql_client, query, variables).values()))
            return gql_client
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _clients_schema():
        """
        The schema PreemptAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Preempt Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'apikey'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('primaryDisplayName')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('hostName') or '')
            device.name = device_raw.get('primaryDisplayName')
            hostname = device_raw.get('hostName')
            if self.__drop_no_hostname is True and not hostname:
                return None
            device.hostname = hostname
            last_seen = parse_date(device_raw.get('mostRecentActivity'))
            if self.__drop_no_last_seen is True and not last_seen:
                return None
            device.last_seen = last_seen
            ip = device_raw.get('lastIpAddress')
            device.risk_score_severity = device_raw.get('riskScoreSeverity')
            if ip and isinstance(ip, str):
                device.add_nic(ips=[ip])
            risk_score = device_raw.get('riskScore')
            if risk_score is not None:
                try:
                    device.risk_score = float(risk_score) * 10.0
                except Exception as e:
                    logger.exception(f'Cant get risk score for {device_raw}')
            device.is_server = device_raw.get('isServer')
            risk_factors = device_raw.get('riskFactors')
            if not isinstance(risk_factors, list):
                risk_factors = []
            for factor_raw in risk_factors:
                try:
                    factor_type = factor_raw.get('type')
                    factor_severiry = factor_raw.get('severity')
                    device.risk_factors.append(RiskFactor(factor_type=factor_type, factor_severiry=factor_severiry))
                except Exception:
                    logger.exception(f'Problem with factor raw {factor_raw}')
            associations = device_raw.get('associations')
            if not isinstance(associations, list):
                associations = []
            users_raw = set()
            for association_raw in associations:
                try:
                    binding_type = association_raw.get('bindingType')
                    entity_raw = association_raw.get('entity')
                    if not isinstance(entity_raw, dict):
                        entity_raw = {}
                    username = entity_raw.get('primaryDisplayName')
                    if not username or not binding_type:
                        continue
                    if binding_type == 'OWNERSHIP':
                        device.owner = username
                        if username not in users_raw:
                            users_raw.add(username)
                            device.last_used_users.append(username)
                    if 'LOGIN' in binding_type:
                        if username not in users_raw:
                            users_raw.add(username)
                            device.last_used_users.append(username)
                    if binding_type == 'LOCAL_ADMINISTRATOR':
                        device.add_local_admin(admin_name=username)
                except Exception:
                    logger.exception(f'Problem with association {association_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Preempt Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'drop_no_last_seen',
                    'title': 'Do not fetch devices without Last Seen',
                    'type': 'bool'
                },
                {
                    'name': 'drop_no_hostname',
                    'title': 'Do not fetch devices without hostname',
                    'type': 'bool'
                }
            ],
            'required': [
                'drop_no_last_seen',
                'drop_no_hostname'
            ],
            'pretty_name': 'Preempt Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'drop_no_last_seen': True,
            'drop_no_hostname': False
        }

    def _on_config_update(self, config):
        self.__drop_no_last_seen = config['drop_no_last_seen']
        self.__drop_no_hostname = config['drop_no_hostname']
