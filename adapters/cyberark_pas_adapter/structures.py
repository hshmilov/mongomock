from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter


class BusinessAddress(SmartJsonClass):
    work_street = Field(str, 'Street')
    work_city = Field(str, 'City')
    work_state = Field(str, 'State')
    work_zip = Field(str, 'Zip Code')
    work_country = Field(str, 'Country')


class Internet(SmartJsonClass):
    home_page = Field(str, 'Home Page')
    home_email = Field(str, 'Home Email')
    other_email = Field(str, 'Other Email')


class Phones(SmartJsonClass):
    home = Field(str, 'Home Number')
    business = Field(str, 'Business Number')
    fax = Field(str, 'Fax Number')
    page = Field(str, 'Page Number')


class PersonDetails(SmartJsonClass):
    street = Field(str, 'Street')
    state = Field(str, 'State')
    zip = Field(str, 'Zip Code')
    organization = Field(str, 'Organization')
    profession = Field(str, 'Profession')
    middleName = Field(str, 'Middle Name')


class CyberarkPasUserInstance(UserAdapter):
    source = Field(str, 'Source')
    change_password_next_login = Field(bool, 'Change Password Next Login')
    user_type = Field(str, 'User Type')
    unauthorized_interfaces = ListField(str, 'Unauthorized Interfaces')
    location = Field(str, 'Vault Location')
    suspended = Field(bool, 'Suspended')
    authentication_methods = ListField(str, 'Authentication Methods')
    vault_authorization = ListField(str, 'Vault Authorization')
    business_address = Field(BusinessAddress, 'Business Address')
    internet = Field(Internet, 'Internet')
    phones = Field(Phones, 'Phones')
    personal_details = Field(PersonDetails, 'Personal Details')
