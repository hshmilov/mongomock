import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from azure_ad_adapter.connection import AUTHORITY_HOST_URL, AzureAdClient

logger = logging.getLogger(f'axonius.{__name__}')


AZURE_CLIENT_ID = 'client_id'
AZURE_CLIENT_SECRET = 'client_secret'
AZURE_TENANT_ID = 'tenant_id'


# pylint: disable=invalid-name,too-many-instance-attributes,arguments-differ
class AzureAdAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        azure_device_id = Field(str, 'Azure Device ID')
        azure_display_name = Field(str, 'Azure Display Name')
        azure_is_compliant = Field(bool, 'Azure Is Compliant')
        azure_is_managed = Field(bool, 'Azure Is Managed')
        ad_on_premise_last_sync_date_time = Field(datetime.datetime, 'On Premise Last Sync Date Time')
        ad_on_premise_sync_enabled = Field(bool, 'On Premise Sync Enabled')
        ad_on_premise_trust_type = Field(str, 'Azure On Premise Trust Type')

    class MyUserAdapter(UserAdapter, ADEntity):
        ad_on_premise_immutable_id = Field(str, 'On Premise Immutable ID')
        ad_on_premise_sync_enabled = Field(bool, 'On Premise Sync Enabled')
        ad_on_premise_last_sync_date_time = Field(datetime.datetime, 'On Premise Last Sync Date Time)')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return client_config[AZURE_TENANT_ID]

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(AUTHORITY_HOST_URL)

    def _connect_client(self, client_config):
        try:
            connection = AzureAdClient(client_id=client_config[AZURE_CLIENT_ID],
                                       client_secret=client_config[AZURE_CLIENT_SECRET],
                                       tenant_id=client_config[AZURE_TENANT_ID])
            connection.test_connection()
            return connection
        except Exception as e:
            message = 'Error connecting to Azure AD with tenant id {0}, reason: {1}'.format(
                client_config[AZURE_TENANT_ID], str(e))
            logger.exception(f'{self.plugin_unique_name}: {message}')
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, session: AzureAdClient):
        yield from session.get_device_list()

    @staticmethod
    def _query_users_by_client(client_name, session: AzureAdClient):
        yield from session.get_user_list()

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {
                    'name': AZURE_CLIENT_ID,
                    'title': 'Azure Client ID',
                    'type': 'string'
                },
                {
                    'name': AZURE_CLIENT_SECRET,
                    'title': 'Azure Client Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': AZURE_TENANT_ID,
                    'title': 'Azure Tenant ID',
                    'type': 'string'
                },
            ],
            'required': [
                AZURE_CLIENT_ID,
                AZURE_CLIENT_SECRET,
                AZURE_TENANT_ID
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, raw_data):
        for raw_device_data in iter(raw_data):
            try:
                # Schema: https://developer.microsoft.com/en-us/graph/docs/api-reference/v1.0/resources/user
                device = self._new_device_adapter()

                device.id = raw_device_data['id']

                account_enabled = raw_device_data.get('accountEnabled')
                if isinstance(account_enabled, bool):
                    device.device_disabled = not account_enabled

                try:
                    device.last_seen = parse_date(raw_device_data.get('approximateLastSignInDateTime'))
                except Exception:
                    logger.exception(f'Can not parse last seen')

                device.azure_device_id = raw_device_data.get('deviceId')
                device.name = raw_device_data.get('displayName')
                device.azure_display_name = raw_device_data.get('displayName')

                azure_is_compliant = raw_device_data.get('isCompliant')
                if isinstance(azure_is_compliant, bool):
                    device.azure_is_compliant = azure_is_compliant

                azure_is_managed = raw_device_data.get('isManaged')
                if isinstance(azure_is_managed, bool):
                    device.azure_is_managed = azure_is_managed

                azure_sync_enabled = raw_device_data.get('onPremisesSyncEnabled')
                if isinstance(azure_sync_enabled, bool):
                    device.ad_on_premise_sync_enabled = azure_sync_enabled

                try:
                    device.ad_on_premise_last_sync_date_time = parse_date(
                        raw_device_data.get('onPremisesLastSyncDateTime'))
                except Exception:
                    logger.exception(f'Can not parse last sync date time')

                device.ad_on_premise_trust_type = raw_device_data.get('trustType')
                device.figure_os(raw_device_data.get('operatingSystem', ''))
                device.os.build = raw_device_data.get('operatingSystemVersion')

                device.set_raw(raw_device_data)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    def _parse_users_raw_data(self, raw_data):
        for raw_user_data in iter(raw_data):
            try:
                # Schema: https://developer.microsoft.com/en-us/graph/docs/api-reference/v1.0/resources/user
                user = self._new_user_adapter()
                user.id = raw_user_data['id']

                account_enabled = raw_user_data.get('accountEnabled')
                if isinstance(account_enabled, bool):
                    user.account_disabled = not account_enabled

                user.user_city = raw_user_data.get('city')
                user.user_country = raw_user_data.get('country')
                user.user_department = raw_user_data.get('department')
                user.ad_display_name = raw_user_data.get('displayName')
                user.first_name = raw_user_data.get('givenName')
                user.last_name = raw_user_data.get('surname')
                user.user_title = raw_user_data.get('jobTitle')
                user.mail = raw_user_data.get('mail')
                user.user_telephone_number = raw_user_data.get('mobilePhone')

                # On premise settings
                ad_on_premise_samaccountname = raw_user_data.get('onPremisesSamAccountName')
                ad_on_premise_user_principal_name = raw_user_data.get('onPremisesUserPrincipalName')
                azure_user_principal_name = raw_user_data.get('userPrincipalName')

                try:
                    user.ad_sAMAccountName = ad_on_premise_samaccountname

                    if ad_on_premise_user_principal_name:
                        user.ad_user_principal_name = ad_on_premise_user_principal_name
                    else:
                        user.ad_user_principal_name = azure_user_principal_name

                    if ad_on_premise_samaccountname:
                        user.username = ad_on_premise_samaccountname
                    elif ad_on_premise_user_principal_name:
                        user.username = ad_on_premise_user_principal_name
                    else:
                        user.username = azure_user_principal_name
                except Exception:
                    logger.exception('Could not set some on premise values')

                user.domain = raw_user_data.get('onPremisesDomainName')
                user.ad_on_premise_immutable_id = raw_user_data.get('onPremisesImmutableId')
                user.ad_sid = raw_user_data.get('onPremisesSecurityIdentifier')

                ad_on_premise_sync_enabled = raw_user_data.get('onPremisesSyncEnabled')
                if isinstance(ad_on_premise_sync_enabled, bool):
                    user.ad_on_premise_sync_enabled = ad_on_premise_sync_enabled
                try:
                    user.ad_on_premise_last_sync_date_time = parse_date(raw_user_data.get('onPremisesLastSyncDateTime'))
                except Exception:
                    logger.exception(f'Can not parse onPremisesLastSyncDateTime')

                user.set_raw(raw_user_data)
                yield user
            except Exception:
                logger.exception(f'Problem parsing user: {str(raw_user_data)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Manager, AdapterProperty.UserManagement]
