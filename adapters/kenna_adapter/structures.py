from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass


class AssetGroup(SmartJsonClass):
    id = Field(int, 'Group ID')
    name = Field(str, 'Group name')
