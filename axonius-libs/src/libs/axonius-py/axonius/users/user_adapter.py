"""
    For adding new fields, see https://axonius.atlassian.net/wiki/spaces/AX/pages/398819372/Adding+New+Field
"""
import datetime
import typing

from axonius.devices.device_adapter import LAST_SEEN_FIELD
from axonius.fields import Field, JsonStringFormat, JsonArrayFormat, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.mongo_escaping import escape_dict, unescape_dict


class UserAdapterDevice(SmartJsonClass):
    """ A definition for the json-scheme for a device that is associated to a user. """
    device_caption = Field(str, 'Device Name')  # The name of the device to be shown in the gui
    last_use_date = Field(datetime.datetime)
    device_status = Field(str, 'Device Status')


class UserFactor(SmartJsonClass):
    factor_type = Field(str, 'Factor Type')
    factor_status = Field(str, 'Factor Status')
    last_updated = Field(datetime.datetime, 'Last Updated')
    vendor_name = Field(str, 'Vendor Name')
    provider = Field(str, 'Provider')
    created = Field(datetime.datetime, 'Created')


class UserApplication(SmartJsonClass):
    app_name = Field(str, 'Application Name')
    app_links = ListField(str, 'Application URLs')
    app_state = Field(str, 'Application State')
    is_user_removed_from_app = Field(bool, 'Is User Removed From App')


class UserAdapter(SmartJsonClass):
    """ A definition for the json-scheme for a User """
    image = Field(str, 'Image', json_format=JsonStringFormat.image)
    id = Field(str, 'ID')  # Usually username@domain.
    user_sid = Field(str, 'SID')
    mail = Field(str, 'Mail')
    username = Field(str, 'User Name')  # Only username, no domain
    display_name = Field(str, 'Display Name')
    description = Field(str, 'Description')
    domain = Field(str, 'Domain')  # Only domain, e.g. "TestDomain.Test", or the computer name (local user)
    is_admin = Field(bool, 'Is Admin')
    organizational_unit = ListField(str, 'Organizational Unit')
    last_seen_in_devices = Field(datetime.datetime, 'Last Seen In Devices')
    last_seen = Field(datetime.datetime, 'Last Seen In Domain')
    fetch_time = Field(datetime.datetime, 'Fetch Time')
    first_fetch_time = Field(datetime.datetime, 'First Fetch Time')
    associated_devices = ListField(UserAdapterDevice, 'Associated Devices',
                                   json_format=JsonArrayFormat.table)
    is_local = Field(bool, 'Is Local')  # If true, its a local user (self.domain == computer). else, its a domain user.
    is_locked = Field(bool, 'Is Locked')  # If true, account is locked, and the time of lockout is last_lockout_time
    last_lockout_time = Field(datetime.datetime, 'Last Lockout time')
    password_expiration_date = Field(datetime.datetime, 'Password Expiration Date')
    days_until_password_expiration = Field(int, 'Days Until Password Expiration')
    password_never_expires = Field(bool, 'Password Never Expires')
    password_not_required = Field(bool, 'Password Is Not Required')
    account_disabled = Field(bool, 'Account Disabled')
    account_expires = Field(datetime.datetime, 'Account Expiration Date')
    logon_count = Field(int, 'Logon Count')
    last_bad_logon = Field(datetime.datetime, 'Last Bad Logon Date')
    last_password_change = Field(datetime.datetime, 'Last Password Change')
    last_logoff = Field(datetime.datetime, 'Last Logoff Date')
    last_logon = Field(datetime.datetime, 'Last Logon Date')
    last_logon_timestamp = Field(datetime.datetime, 'Last Logon Timestamp Date')
    user_created = Field(datetime.datetime, 'User Creation Date')

    user_title = Field(str, 'User Title')
    user_department = Field(str, 'User Department')
    user_manager = Field(str, 'User Manager Username')
    user_telephone_number = Field(str, 'User Telephone Number')
    user_city = Field(str, 'User City')
    user_country = Field(str, 'User Country')

    first_name = Field(str, 'First Name')
    last_name = Field(str, 'Last Name')

    employee_id = Field(str, 'Employee ID')     # could have letters so its a string
    employee_number = Field(str, 'Employee Number')     # could have letters so its a string
    employee_type = Field(str, 'Employee Type')     # could have letters so its a string

    user_status = Field(str, 'User Status')
    user_apps = ListField(UserApplication, 'Applications')
    user_factors = ListField(UserFactor, 'Authentication Factors')
    groups = ListField(str, 'Groups')
    backup_source = Field(str, 'Backup Source')

    required = ['id', 'username']

    def __init__(self, user_fields: typing.MutableSet[str], user_raw_fields: typing.MutableSet[str]):
        """ The user_fields and user_raw_fields will be auto-populated when new fields are set. """
        super().__init__()
        # do not pass kwargs to constructor before setting up self._user_fields
        # because its supposed to populate the names of the fields into it - see _define_new_name override here
        self._user_fields = user_fields
        self._user_raw_fields = user_raw_fields
        self._raw_data = {}  # will hold any extra raw fields that are associated with this device.

    def _define_new_name(self, name: str):
        if name.startswith('raw.'):
            target_field_list = self._user_raw_fields
        else:
            target_field_list = self._user_fields
        target_field_list.add(name)

    # pylint: disable=arguments-differ
    def declare_new_field(self, *args, **kwargs):
        assert self.__class__ != UserAdapter, \
            'Can not change UserAdapter, its generic! ' \
            'see test_smart_json_class.py::test_schema_change_for_special_classes'
        super().declare_new_field(*args, **kwargs)
    # pylint: enable=arguments-differ

    def add_associated_device(self, **kwargs):
        self.associated_devices.append(UserAdapterDevice(**kwargs))

    def add_user_factor(self, **kwargs):
        self.user_factors.append(UserFactor(**kwargs))

    def add_user_application(self, **kwargs):
        self.user_apps.append(UserApplication(**kwargs))

    def set_raw(self, raw_data: dict):
        """ Sets the raw fields associated with this device and also updates user_raw_fields.
            Use only this function because it also fixes '.' in the keys such that it will work on MongoDB.
        """
        assert isinstance(raw_data, dict)
        raw_data = escape_dict(raw_data)
        self._raw_data = raw_data
        self._dict['raw'] = self._raw_data
        self._extend_names('raw', raw_data)

    def get_raw(self):
        return unescape_dict(self._raw_data)


assert UserAdapter.last_seen.name == LAST_SEEN_FIELD


ASSOCIATED_FIELD = ['mail', 'user_department', 'ad_display_name', 'division', 'company']
