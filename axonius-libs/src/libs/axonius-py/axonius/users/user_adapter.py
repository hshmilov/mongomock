import typing
import datetime
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.mongo_escaping import escape_dict

"""
    For adding new fields, see https://axonius.atlassian.net/wiki/spaces/AX/pages/398819372/Adding+New+Field
"""


class UserAdapterDevice(SmartJsonClass):
    """ A definition for the json-scheme for a device that is associated to a user. """
    device_caption = Field(str, "Associated Device Name")  # The name of the device to be shown in the gui

    adapter_unique_name = Field(str)  # the adapter unique name of the device
    adapter_data_id = Field(str)
    last_use_date = Field(datetime.datetime)


class UserAdapter(SmartJsonClass):
    """ A definition for the json-scheme for a User """

    image = Field(str, "Image", json_format=JsonStringFormat.image)
    id = Field(str, "ID")  # Usually username@domain.
    username = Field(str, 'User Name')  # Only username, no domain
    domain = Field(str, "Domain")   # Only domain, e.g. "TestDomain.Test", or the computer name (local user)
    is_admin = Field(bool, "Is Admin")
    last_seen_in_devices = Field(datetime.datetime, 'Last Seen In Devices')
    last_seen_in_domain = Field(datetime.datetime, 'Last Seen In Domain')
    associated_devices = ListField(UserAdapterDevice, "Associated Devices",
                                   json_format=JsonStringFormat.associated_device)
    member_of = ListField(str, "Member Of")
    is_local = Field(bool, "Is Local")  # If true, its a local user (self.domain == computer). else, its a domain user.
    is_locked = Field(bool, "Is Locked")  # If true, account is locked, and the time of lockout is last_lockout_time
    last_lockout_time = Field(datetime.datetime, "Last Lockout time")
    password_expiration_date = Field(datetime.datetime, "Password Expiration Date")
    password_never_expires = Field(bool, "Password Never Expires")
    password_not_required = Field(bool, "Password Is Not Required")
    account_enabled = Field(bool, "Account Enabled")
    account_expires = Field(datetime.datetime, "Account Expiration Date")
    last_bad_logon = Field(datetime.datetime, "Domain Last Bad Logon Date")
    last_password_change = Field(datetime.datetime, "Last Password Change")
    last_logoff = Field(datetime.datetime, "Domain Last Logoff Date")
    last_logon = Field(datetime.datetime, "Domain Last Logon Date")
    user_created = Field(datetime.datetime, "User Creation Date")

    required = ['id', 'username', 'domain']

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

    def add_associated_device(self, **kwargs):
        self.associated_devices.append(UserAdapterDevice(**kwargs))

    def set_raw(self, raw_data: dict):
        """ Sets the raw fields associated with this device and also updates user_raw_fields.
            Use only this function because it also fixes '.' in the keys such that it will work on MongoDB.
        """
        assert isinstance(raw_data, dict)
        raw_data = escape_dict(raw_data)
        self._raw_data = raw_data
        self._dict['raw'] = self._raw_data
        self._extend_names('raw', raw_data)


USER_LAST_SEEN_FIELD = UserAdapter.last_seen_in_domain.name
