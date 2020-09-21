import datetime
import logging

from axonius.clients.azure.structures import AzureAdapterEntity
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter

logger = logging.getLogger(f'axonius.{__name__}')


AZURE_AD_DEVICE_TYPE = 'Azure AD'
INUTE_DEVICE_TYPE = 'Intune'


class EmailActivity(SmartJsonClass):
    is_deleted = Field(bool, 'Deleted')
    deleted_date = Field(datetime.datetime, 'Deleted Date')
    send_count = Field(int, 'Send Count')
    receive_count = Field(int, 'Receive Count')
    read_count = Field(int, 'Read Count')
    report_date = Field(datetime.datetime, 'Report Date')
    report_period = Field(int, 'Report Period')
    product_license = Field(str, 'License')


class AzureADDevice(DeviceAdapter):
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


class AzureADUser(UserAdapter, ADEntity, AzureAdapterEntity):
    account_tag = Field(str, 'Account Tag')
    ad_on_premise_immutable_id = Field(str, 'On Premise Immutable ID')
    ad_on_premise_sync_enabled = Field(bool, 'On Premise Sync Enabled')
    ad_on_premise_last_sync_date_time = Field(datetime.datetime, 'On Premise Last Sync Date Time)')
    is_resource_account = Field(bool, 'Is Resource Account')
    user_type = Field(str, 'User Type', enum=['Member', 'Guest'])
    # This data is collected from Office 365.
    email_activity = Field(EmailActivity, 'Email Activity')
