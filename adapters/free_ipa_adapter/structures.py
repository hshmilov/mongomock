from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter


class FreeIpaDeviceInstance(DeviceAdapter):
    user_class = Field(str, 'User Class')
    member_roles = ListField(str, 'Member Of Roles')
    member_host_groups = ListField(str, 'Member Host Groups')
    managed_by_host = ListField(str, 'Managed By Host')
    managing_host = ListField(str, 'Managing Host')


class FreeIpaUserInstance(UserAdapter):
    user_class = Field(str, 'Class')
    fax_number = ListField(str, 'Fax Numbers')
    telephone_numbers = ListField(str, 'Telephone Numbers')
    mobile_numbers = ListField(str, 'Mobile Numbers')
    preferred_language = Field(str, 'Preferred Language')
    postal_code = Field(str, 'Postal Code')
    state = Field(str, 'State')
    street = Field(str, 'Street')
    mails = ListField(str, 'Mails')
    member_roles = ListField(str, 'Member Of Roles')
    home_directory = Field(str, 'Home Directory')
    principal_name = Field(str, 'Principal Name')
