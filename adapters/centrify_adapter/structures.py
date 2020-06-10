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
