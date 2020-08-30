import datetime

from axonius.smart_json_class import SmartJsonClass

from axonius.fields import Field, ListField, JsonArrayFormat
from axonius.users.user_adapter import UserAdapter


class CentrifyAccessListItem(SmartJsonClass):
    access_type = Field(str, 'Access Granted By')
    item_id = Field(str, 'Role or User UUID')
    name = Field(str, 'Role or User Name', description='"User" means direct access')


class CentrifyUPData(SmartJsonClass):
    is_intranet = Field(bool, 'Intranet App')
    rowkey = Field(str, 'Application ID')
    admin_tag = Field(str, 'Admin Tag')
    category = Field(str, 'Category')
    shortcut = Field(bool, 'Optional Installation (Shortcut)')
    display_name = Field(str, 'Application Display Name')
    app_type = Field(str, 'Application Type')
    is_username_ro = Field(bool, 'Username Read Only')
    is_password_set = Field(bool, 'Password Set')
    app_key = Field(str, 'App Key')
    rank = Field(int, 'Application Rank')
    webapp_type_name = Field(str, 'Webapp Type Display Name')
    app_username = Field(str, 'Application Username')
    template_name = Field(str, 'Application Template Name')
    app_type_name = Field(str, 'Application Type Display Name')
    automatic = Field(bool, 'Automatic Installation Set')
    url = Field(str, 'Application URL')
    webapp_type = Field(str, 'Webapp Type')
    description = Field(str, 'Description')
    name = Field(str, 'Name')
    access_list = ListField(CentrifyAccessListItem, 'Access Grants List')


class CentrifyUserInstance(UserAdapter):
    # immediate fields
    uuid = Field(str, 'UUID')
    reports_to = Field(str, 'Reports To (UUID)')
    preferred_culture = Field(str, 'Preferred Culture')
    office_number = Field(str, 'Office Number')
    mobile_number = Field(str, 'Mobile Number')
    home_number = Field(str, 'Home Number')
    # UPdata fields
    centrify_apps = ListField(CentrifyUPData, 'User Portal Applications', json_format=JsonArrayFormat.table)
    # Fields for redrock query users
    active_sessions = Field(int, 'Active Sessions')
    active_checkouts = Field(int, 'Active Checkouts')
    rights = Field(str, 'Permissions')
    healthy = Field(str, 'Last Health Status')
    health_err = Field(str, 'Health Check Error Message')
    use_wheel = Field(bool, 'Proxy Used')
    is_managed = Field(bool, 'Account Managed')
    cred_id = Field(str, 'Vault Credential ID')
    cred_type = Field(str, 'Vauld Credential Type')
    pwd_reset_status = Field(str, 'Password Reset State')
    pwd_reset_retries = Field(int, 'Password Reset Retry Count')
    pwd_reset_last_err = Field(str, 'Last Password Reset Error')
    due_back = Field(datetime.datetime, 'Checkouts Expire')
    last_change = Field(datetime.datetime, 'Password Last Modified')
    workflow_enabled = Field(bool, 'Work Flow Enabled')
    workflow_enabled_effective = Field(bool, 'Work Flow Enabled (Global)')
    missing_password = Field(bool, 'Missing Password')
    last_health_check = Field(datetime.datetime, 'Last Health Check')
    # Field for redrock query users from other tables / foreign keys
    session_type = Field(str, 'Session Type')
    computer_class = Field(str, 'Host Resource Type')
    fqdn = Field(str, 'Host Resource FQDN')
    owner_id = Field(str, 'Resource Owner ID')
    owner_name = Field(str, 'Resource Owner Name')
    host_uuid = Field(str, 'Host Resource UUID')
    domain_id = Field(str, 'Domain Resource ID')
    db_id = Field(str, 'Database Resource ID')
    resource_name = Field(str, 'Resource Name')
    device_id = Field(str, 'Device Resource ID')
    discover_time = Field(datetime.datetime, 'Discovery Time')
