from datetime import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter


class PrivxSupportedService(SmartJsonClass):
    service_name = Field(str, 'Service Name')
    address = Field(str, 'Address')
    auth_type = Field(str, 'Authentication Type')
    login_page_url = Field(str, 'Login Page URL')
    login_request_password_property = Field(str, 'Login Request Password Property')
    login_request_url = Field(str, 'Login Request URL')
    password_field_name = Field(str, 'Password Field Name')
    port = Field(int, 'Port')
    source = Field(str, 'Source')
    status = Field(str, 'Status')
    status_updated = Field(str, 'Status Updated')
    username_field_name = Field(str, 'Username Field Name')


class Role(SmartJsonClass):
    id = Field(str, 'ID')
    name = Field(str, 'Name')


class Principal(SmartJsonClass):
    name = Field(str, 'Name')
    source = Field(str, 'Source')
    use_user_account = Field(bool, 'Use User Account')
    roles = ListField(Role, 'Roles')


class PrivxUserInstance(UserAdapter):
    password_change_required = Field(bool, 'Password Change Required')
    user_update_time = Field(datetime, 'Last Updated')
    windows_account = Field(str, 'Windows Account')
    unix_account = Field(str, 'Unix Account')


class PrivxDeviceInstance(DeviceAdapter):
    cloud_provider_region = Field(str, 'Cloud Provider Region')
    audit_enabled = Field(bool, 'Audit Enabled')
    contact_address = Field(str, 'Contact Address')
    deployable = Field(bool, 'Deployable')
    distinguished_name = Field(str, 'Distinguished Name')
    external_id = Field(str, 'External ID')
    host_classification = Field(str, 'Host Classification')
    host_type = Field(str, 'Host Type')
    instance_id = Field(str, 'Instance ID')
    organization = Field(str, 'Organization')
    principals = ListField(Principal, 'Principals')
    privx_configured = Field(str, 'Privx Configured')
    supported_services = ListField(PrivxSupportedService, 'Supported Services')
    source_id = Field(str, 'Source ID')
    tofu = Field(bool, 'Tofu')
    updated_by = Field(str, 'Updated By')
    zone = Field(str, 'Zone')
