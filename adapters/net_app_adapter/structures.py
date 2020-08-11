from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter


class HighAvailability(SmartJsonClass):
    auto_giveback = Field(bool, 'Auto Giveback')
    partners = ListField(str, 'Nodes in High Availability Group')
    enabled = Field(bool, 'Storage Failover Enabled')


class Version(SmartJsonClass):
    generation = Field(int, 'Generation')
    minor = Field(int, 'Minor')
    major = Field(int, 'Major')
    full = Field(str, 'Full')


class NetAppDeviceInstance(DeviceAdapter):
    high_availability = Field(HighAvailability, 'High Availability')
    membership = Field(str, 'Membership', enum=['available', 'joining', 'member'])
    version = Field(Version, 'Cluster Version')
    over_temperature = Field(str, 'Hardware Temperature', enum=['over', 'normal'])


class AccountApplication(SmartJsonClass):
    authentication_methods = ListField(str, 'Authentication Methods')
    application = Field(str, 'Application', enum=['console', 'http', 'ontapi', 'service_processor', 'ssh'])
    second_authentication_method = (str, 'Second Authentication Method for MFA')


class NetAppUserInstance(UserAdapter):
    svm_name = Field(str, 'SVM Name')
    svm_uuid = Field(str, 'SVM UUID')
    scope = Field(str, enum=['cluster', 'svm'])
    applications = ListField(AccountApplication, 'Account Applications')
