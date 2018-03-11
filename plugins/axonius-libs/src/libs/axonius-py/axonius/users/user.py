import typing
import datetime
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.mongo_escaping import escape_dict
from axonius.parsing_utils import format_image

"""
    For adding new fields, see https://axonius.atlassian.net/wiki/spaces/AX/pages/398819372/Adding+New+Field
"""


class UserDevice(SmartJsonClass):
    """ A definition for the json-scheme for a device that is associated to a user. """
    plugin_unique_name = Field(str)
    # TODO: An enum of all adapters here.
    adapter_name = Field(str, "Adapter Name")
    adapter_id = Field(str, "Unique ID By Adapter")


class User(SmartJsonClass):
    """ A definition for the json-scheme for a User """

    id = Field(str, "ID")  # Usually the same as username.
    username = Field(str, 'User Name')  # Only username, no domain
    domain = Field(str, "Domain")   # Only domain, e.g. "TestDomain.Test"
    last_seen = Field(datetime.datetime, 'Last Seen')
    associated_devices = ListField(UserDevice, "Associated Devices")
    member_of = ListField(str, "Member Of")
    is_admin = Field(bool, "Is Admin")
    account_expires = Field(datetime.datetime, "Account Expiration Date")
    last_bad_logon = Field(datetime.datetime, "Last Bad Logon Date")
    last_password_change = Field(datetime.datetime, "Last Password Change")
    last_logoff = Field(datetime.datetime, "Last Logoff Date")
    last_logon = Field(datetime.datetime, "Last Logon Date")
    user_created = Field(datetime.datetime, "User Creation Date")
    image = Field(str, "Image", converter=format_image, json_format=JsonStringFormat.image)

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

    def set_raw(self, raw_data: dict):
        """ Sets the raw fields associated with this device and also updates user_raw_fields.
            Use only this function because it also fixes '.' in the keys such that it will work on MongoDB.
        """
        assert isinstance(raw_data, dict)
        raw_data = escape_dict(raw_data)
        self._raw_data = raw_data
        self._dict['raw'] = self._raw_data
        self._extend_names('raw', raw_data)


USER_LAST_SEEN_FIELD = User.last_seen.name
