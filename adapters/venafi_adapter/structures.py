import datetime

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class VenafiCertificateInstance(DeviceAdapter):
    parent_dn = Field(str, 'Parent DN')
    schema_class = Field(str, 'Schema Class')
    approver = Field(str, 'Approver')
    authority_dn = Field(str, 'Authority DN')
    contact = Field(str, 'Contact')
    management_type = Field(str, 'Management Type')
    issuer = Field(str, 'Issuer')
    subject = Field(str, 'Subject')
    thump_print = Field(str, 'Thumb Print')
    valid_from = Field(datetime.datetime, 'Valid From')
    valid_to = Field(datetime.datetime, 'Valid To')
