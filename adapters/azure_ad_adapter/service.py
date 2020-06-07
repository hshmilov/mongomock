import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.azure.consts import AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID, AZURE_VERIFY_SSL, \
    AZURE_AUTHORIZATION_CODE, AZURE_ACCOUNT_TAG, AZURE_IS_AZURE_AD_B2C, AZURE_AD_CLOUD_ENVIRONMENT, AZURE_HTTPS_PROXY
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from azure_ad_adapter.connection import AUTHORITY_HOST_URL, AzureAdClient

logger = logging.getLogger(f'axonius.{__name__}')


AZURE_AD_DEVICE_TYPE = 'Azure AD'
INUTE_DEVICE_TYPE = 'Intune'


# pylint: disable=invalid-name,too-many-instance-attributes,arguments-differ
class AzureAdAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        azure_ad_device_type = Field(str, 'Azure AD Device Type', enum=[AZURE_AD_DEVICE_TYPE, INUTE_DEVICE_TYPE])
        account_tag = Field(str, 'Account Tag')
        azure_device_id = Field(str, 'Azure Device ID')
        azure_display_name = Field(str, 'Azure Display Name')
        azure_is_compliant = Field(bool, 'Azure Is Compliant')
        azure_is_managed = Field(bool, 'Azure Is Managed')
        ad_on_premise_last_sync_date_time = Field(datetime.datetime, 'On Premise Last Sync Date Time')
        ad_on_premise_sync_enabled = Field(bool, 'On Premise Sync Enabled')
        ad_on_premise_trust_type = Field(str, 'Azure On Premise Trust Type')
        android_security_patch_level = Field(str, 'Android Security Patch Level')
        phone_number = Field(str, 'Phone Number')
        imei = Field(str, 'IMEI')
        is_encrypted = Field(bool, 'Is Encrypted')
        user_principal_name = Field(str, 'User Principal Name')
        managed_device_name = Field(str, 'Managed Device Name')
        azure_ad_id = Field(str)
        last_sign_in = Field(datetime.datetime, 'Approximate Last SignIn Time')
        compliance_state = Field(str, 'Compliance State')
        grace_period_expiration = Field(datetime.datetime, 'Compliance Grace Period Expiration Date Time')
        device_enrollment_type = Field(str, 'Device Enrollment Type')
        device_registration_state = Field(str, 'Device Registration State')
        eas_activated = Field(bool, 'EAS Activated')
        enrolled_time = Field(datetime.datetime, 'Enrolled Date Time')

    class MyUserAdapter(UserAdapter, ADEntity):
        account_tag = Field(str, 'Account Tag')
        ad_on_premise_immutable_id = Field(str, 'On Premise Immutable ID')
        ad_on_premise_sync_enabled = Field(bool, 'On Premise Sync Enabled')
        ad_on_premise_last_sync_date_time = Field(datetime.datetime, 'On Premise Last Sync Date Time)')
        is_resource_account = Field(bool, 'Is Resource Account')
        user_type = Field(str, 'User Type', enum=['Member', 'Guest'])

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return client_config[AZURE_TENANT_ID]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(AUTHORITY_HOST_URL)

    def _connect_client(self, client_config):
        try:
            connection = AzureAdClient(client_id=client_config[AZURE_CLIENT_ID],
                                       client_secret=client_config[AZURE_CLIENT_SECRET],
                                       tenant_id=client_config[AZURE_TENANT_ID],
                                       https_proxy=client_config.get(AZURE_HTTPS_PROXY),
                                       verify_ssl=client_config.get(AZURE_VERIFY_SSL),
                                       is_azure_ad_b2c=client_config.get(AZURE_IS_AZURE_AD_B2C),
                                       azure_region=client_config.get(AZURE_AD_CLOUD_ENVIRONMENT),
                                       allow_beta_api=self.__allow_beta_api,
                                       allow_fetch_mfa=self.__allow_fetch_mfa,
                                       parallel_count=self.__parallel_count,
                                       async_retry_time=self.__async_retry_time,
                                       async_retry_max=self.__async_retries_max
                                       )
            auth_code = client_config.get(AZURE_AUTHORIZATION_CODE)
            refresh_tokens_db = self._get_collection('refresh_tokens')
            rt_doc = refresh_tokens_db.find_one({'auth_code': auth_code})
            try:
                if auth_code:
                    if auth_code.startswith('refresh-'):
                        refresh_token = auth_code[len('refresh-'):]
                    elif rt_doc:
                        refresh_token = rt_doc['refresh_token']
                    else:
                        refresh_token = connection.get_refresh_token_from_authorization_code(auth_code)
                        # client_config[AZURE_AUTHORIZATION_CODE] = 'refresh-' + refresh_token  # override refresh token
                        refresh_tokens_db.update_one(
                            {'auth_code': auth_code},
                            {
                                '$set': {'refresh_token': refresh_token}
                            },
                            upsert=True
                        )

                    connection.set_refresh_token(refresh_token)

                connection.test_connection()
            except Exception as e:
                if 'expired' in str(e).lower():
                    raise ClientConnectionException(f'Token has expired. Please follow the documentation to '
                                                    f're-set the token. Full message: {str(e)}')
                raise
            metadata_dict = dict()
            if client_config.get(AZURE_ACCOUNT_TAG):
                metadata_dict[AZURE_ACCOUNT_TAG] = client_config.get(AZURE_ACCOUNT_TAG)
            return connection, metadata_dict
        except Exception as e:
            message = 'Error connecting to Azure AD with tenant id {0}, reason: {1}'.format(
                client_config[AZURE_TENANT_ID], str(e))
            logger.exception(f'{self.plugin_unique_name}: {message}')
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, data):
        session, metadata = data
        return session.get_device_list(), metadata

    @staticmethod
    def _query_users_by_client(client_name, data):
        session, metadata = data
        return session.get_user_list(), metadata

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
                {
                    'name': AZURE_AD_CLOUD_ENVIRONMENT,
                    'title': 'Cloud Environment',
                    'type': 'string',
                    'enum': ['Global', 'China'],    # if you add something here, change azure_cis_account_report.py
                    'default': 'Global'
                },
                {
                    'name': AZURE_AUTHORIZATION_CODE,
                    'title': 'Azure Oauth Authorization Code',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': AZURE_IS_AZURE_AD_B2C,
                    'title': 'Is Azure AD B2C',
                    'type': 'bool'
                },
                {
                    'name': AZURE_ACCOUNT_TAG,
                    'title': 'Account Tag',
                    'type': 'string'
                },
                {
                    'name': AZURE_VERIFY_SSL,
                    'title': 'Verify SSL',
                    'type': 'bool',
                    'default': True
                },
                {
                    'name': AZURE_HTTPS_PROXY,
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                AZURE_CLIENT_ID,
                AZURE_CLIENT_SECRET,
                AZURE_TENANT_ID,
                AZURE_AD_CLOUD_ENVIRONMENT,
                AZURE_VERIFY_SSL,
                AZURE_IS_AZURE_AD_B2C
            ],
            'type': 'array'
        }

    def _create_azure_ad_device(self, raw_device_data):
        try:
            # Schema: https://developer.microsoft.com/en-us/graph/docs/api-reference/v1.0/resources/user
            device = self._new_device_adapter()
            device.azure_ad_device_type = AZURE_AD_DEVICE_TYPE
            device.id = raw_device_data['id'] + '_' + (raw_device_data.get('displayName') or '')

            account_enabled = raw_device_data.get('accountEnabled')
            if isinstance(account_enabled, bool):
                device.device_disabled = not account_enabled

            try:
                device.last_sign_in = parse_date(raw_device_data.get('approximateLastSignInDateTime'))
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
            device.adapter_properties = [AdapterProperty.Assets.name, AdapterProperty.Manager.name]
            device.set_raw(raw_device_data)
            return device
        except Exception:
            logger.exception(f'Got exception for raw_device_data: {raw_device_data}')
            return None

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_intune_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.azure_ad_device_type = INUTE_DEVICE_TYPE
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('deviceName') or '')
            device.name = device_raw.get('deviceName')
            device.grace_period_expiration = parse_date(device_raw.get('complianceGracePeriodExpirationDateTime'))
            device.device_manufacturer = device_raw.get('manufacturer')
            device.compliance_state = device_raw.get('complianceState')
            device.device_enrollment_type = device_raw.get('deviceEnrollmentType')
            device.device_registration_state = device_raw.get('deviceRegistrationState')
            device.eas_activated = device_raw.get('easActivated') \
                if isinstance(device_raw.get('easActivated'), bool) else None
            device.device_model = device_raw.get('model')
            try:
                total_storage_space_in_gb = int(device_raw.get('totalStorageSpaceInBytes')) / (1024.0 ** 3)
                free_storage_space_in_gb = int(device_raw.get('freeStorageSpaceInBytes')) / (1024.0 ** 3)
                device.add_hd(total_size=total_storage_space_in_gb,
                              free_size=free_storage_space_in_gb)
            except Exception:
                logger.exception(f'Problem getting storage')
            device.managed_device_name = device_raw.get('managedDeviceName')
            try:
                device.figure_os((device_raw.get('osVersion') or '') + ' ' +
                                 ((device_raw.get('operatingSystem')) or ''))
                try:
                    if device.os.type == 'Windows':
                        device.hostname = device.name
                except Exception:
                    pass
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            device.imei = device_raw.get('imei')
            try:
                device.last_seen = parse_date(device_raw.get('lastSyncDateTime'))
            except Exception:
                logger.exception(f'Prbolem getting last seen for {device_raw}')
            device_serial = device_raw.get('serialNumber')
            if device_serial and device_serial not in ['SystemSerialNumber', 'System Serial Number', 'Default string']:
                device.device_serial = device_serial
            device.phone_number = device_raw.get('phoneNumber')
            device.android_security_patch_level = device_raw.get('androidSecurityPatchLevel')
            device.email = device_raw.get('emailAddress')
            device.enrolled_time = parse_date(device_raw.get('enrolledDateTime'))
            if device_raw.get('wiFiMacAddress'):
                device.add_nic(device_raw.get('wiFiMacAddress'), None)
            device.is_encrypted = device_raw.get('isEncrypted')
            device.user_principal_name = device_raw.get('userPrincipalName')
            device.azure_ad_id = device_raw.get('azureADDeviceId')
            try:
                installed_apps = device_raw.get('installed_apps') or []
                for app in installed_apps:
                    if app.get('displayName'):
                        device.add_installed_software(name=app.get('displayName'), version=app.get('version'))
            except Exception:
                logger.exception(f'Cant parse installed apps for device {device_id}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with device {device_raw}')
            return None

    def _parse_raw_data(self, raw_data_all):
        raw_data, metadata = raw_data_all
        for raw_device_data, devie_type in iter(raw_data):
            try:
                if self.__fields_to_exclude:
                    for field_to_exclude in self.__fields_to_exclude.split(','):
                        raw_device_data.pop(field_to_exclude.strip(), None)
            except Exception:
                logger.exception(f'Could not exclude fields {str(self.__fields_to_exclude)}')
            device = None
            if devie_type == 'Azure AD':
                device = self._create_azure_ad_device(raw_device_data)
            if devie_type == 'Intune':
                device = self._create_intune_device(raw_device_data)
            if device:
                device.account_tag = metadata.get(AZURE_ACCOUNT_TAG)
                yield device

    # pylint: disable=too-many-locals
    def _parse_users_raw_data(self, raw_data_all):
        raw_data, metadata = raw_data_all
        for raw_user_data in iter(raw_data):
            try:
                try:
                    if self.__fields_to_exclude:
                        for field_to_exclude in self.__fields_to_exclude.split(','):
                            raw_user_data.pop(field_to_exclude.strip(), None)
                except Exception:
                    logger.exception(f'Could not exclude fields {str(self.__fields_to_exclude)}')
                # Schema: https://developer.microsoft.com/en-us/graph/docs/api-reference/v1.0/resources/user
                user = self._new_user_adapter()
                user_id = raw_user_data.get('id') or raw_user_data.get('objectId')
                if not user_id:
                    logger.warning(f'Warning - no user id for {raw_user_data}, bypassing')
                    continue
                user.id = str(user_id)
                user.account_tag = metadata.get(AZURE_ACCOUNT_TAG)

                account_enabled = raw_user_data.get('accountEnabled')
                if isinstance(account_enabled, bool):
                    user.account_disabled = not account_enabled

                mail = raw_user_data.get('mail')
                try:
                    if not mail:
                        for sign_in_name_raw in (raw_user_data.get('signInNames') or []):
                            if sign_in_name_raw.get('type') == 'emailAddress':
                                mail = sign_in_name_raw.get('value')
                                break

                    if not mail:
                        other_mails = raw_user_data.get('otherMails')
                        if other_mails and isinstance(other_mails, list) and len(other_mails) > 0:
                            mail = other_mails[0]
                except Exception:
                    logger.exception(f'Failed parsing mail for user {raw_user_data}')

                user.user_city = raw_user_data.get('city')
                user.user_country = raw_user_data.get('country')
                user.user_department = raw_user_data.get('department')
                user.ad_display_name = raw_user_data.get('displayName')
                user.first_name = raw_user_data.get('givenName')
                user.last_name = raw_user_data.get('surname')
                user.user_title = raw_user_data.get('jobTitle')
                user.mail = mail
                user.user_telephone_number = raw_user_data.get('mobilePhone')

                user_type = raw_user_data.get('userType')
                if user_type in ['Guest', 'Member']:
                    user.user_type = user_type

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
                    # warning(exception), but continue running
                    logger.exception(f'Can not parse onPremisesLastSyncDateTime')

                # groups
                user_groups = raw_user_data.get('memberOf')
                if isinstance(user_groups, list):
                    groups = list()
                    for group in user_groups:
                        if not isinstance(group, dict):
                            continue
                        group_name = group.get('displayName')
                        if group_name and isinstance(group_name, str):
                            groups.append(group_name)
                    try:
                        user.groups = groups
                    except Exception:
                        logger.warning(f'Failed to parse groups for {user_id} from {user_groups}')
                if not user_groups:
                    # warn, but continue running (fallthrough!)
                    logger.warning(f'Group information not available for {user_id}')

                # last logon
                login_dict = raw_user_data.get('signInActivity')
                if login_dict and isinstance(login_dict, dict):
                    user.last_logon = parse_date(login_dict.get('lastSignInDateTime'))
                else:
                    # warn, but continue running
                    logger.warning(f'Sign in activity not available for {user_id}')

                # mfa
                user_mfa_data = raw_user_data.get('credsDetails')
                if user_mfa_data:
                    if isinstance(user_mfa_data, list):
                        user_mfa_data = user_mfa_data[0]  # safeguard, this should never happen.
                    if isinstance(user_mfa_data, dict):
                        factors = user_mfa_data.get('authMethods') or []
                        factor_status = user_mfa_data.get('isMfaRegistered')
                        if not isinstance(factor_status, bool):
                            factor_status = None
                        for factor in factors:
                            try:
                                user.add_user_factor(
                                    factor_type=factor,
                                    factor_status=factor_status
                                )
                            except Exception:
                                logger.warning(f'Failed to parse user mfa info from {user_mfa_data}')

                # last password change
                user.last_password_change = parse_date(raw_user_data.get('lastPasswordChangeDateTime'))
                # employee id
                user.employee_id = raw_user_data.get('employeeId')
                # user created
                user.user_created = parse_date(raw_user_data.get('createdDateTime'))
                # is resource account
                is_resource_account = raw_user_data.get('is_resource_account')
                if isinstance(is_resource_account, bool):
                    user.is_resource_account = is_resource_account

                # set raw
                user.set_raw(raw_user_data)
                yield user
            except Exception:
                logger.exception(f'Problem parsing user: {str(raw_user_data)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fields_to_exclude',
                    'title': 'Fields to exclude',
                    'type': 'string'
                },
                {
                    'name': 'allow_beta_api',
                    'title': 'Allow use of BETA API endpoints',
                    'type': 'bool',
                    'description': 'Required currently in order to allow '
                                   'fetching users last log-on date and MFA enrollment status',
                },
                {
                    'name': 'allow_fetch_mfa',
                    'title': 'Allow fetching MFA enrollment status for users',
                    'type': 'bool',
                    'description': 'Currently requires use of BETA API, as well as Reports.Read.All permissions.'
                },
                {
                    'name': 'parallel_count',
                    'title': 'Number of parallel requests',
                    'type': 'integer'
                },
                {
                    'name': 'retry_max',
                    'title': 'Max retry count for parallel requests',
                    'type': 'integer'
                },
                {
                    'name': 'async_error_sleep_time',
                    'title': 'Time in seconds to wait between retries of parallel requests',
                    'type': 'integer'
                }
            ],
            'required': [
                'allow_beta_api',
                'allow_fetch_mfa'
            ],
            'pretty_name': 'Azure AD Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fields_to_exclude': None,
            'allow_beta_api': False,
            'allow_fetch_mfa': False,
            'parallel_count': 10,
            'retry_max': 3,
            'async_error_sleep_time': 3,
        }

    def _on_config_update(self, config):
        logger.info(f'Got new advanced configuration: {config}')
        self.__fields_to_exclude = config['fields_to_exclude']
        self.__allow_beta_api = config['allow_beta_api']
        self.__allow_fetch_mfa = config['allow_fetch_mfa']
        if self.__allow_fetch_mfa and not self.__allow_beta_api:
            logger.warning(f'NOTICE: allow_fetch_mfa is on but allow_beta_api is off,'
                           f' even though fetching mfa requires beta api!')
        self.__async_retries_max = config['retry_max']
        self.__parallel_count = config['parallel_count']
        self.__async_retry_time = config['async_error_sleep_time']
