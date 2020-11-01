from axonius.fields import ListField, Field
from axonius.users.user_adapter import UserAdapter


class LyncUserInstance(UserAdapter):
    email_addresses = ListField(str, 'Email Addresses')
    mobile_phone_number = Field(str, 'Mobile Phone Number')
    office_phone_number = Field(str, 'Office Phone Number')
    other_phone_number = Field(str, 'Other Phone Number')
    work_phone_number = Field(str, 'Work Phone Number')
