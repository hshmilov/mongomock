import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field


# pylint: disable=too-many-instance-attributes
class VectraInstance(DeviceAdapter):
    c_score = Field(int, 'Certainty score')
    c_score_gte = Field(int, 'Certainty score greater than or equal to')
    fields = Field(str, 'Filtered fields in return object')
    is_key_asset = Field(bool, 'Is device key asset')
    last_detection_timestamp = Field(datetime.datetime, 'Timestamp of last detection')
    ordering = Field(str, 'Field to use for ordering response')
    page = Field(int, 'Number of page to return')
    page_size = Field(int, 'Number of objects per page or all')
    state = Field(str, 'State')
    t_score = Field(int, 'Threat score')
    t_score_gte = Field(int, 'Threat score greater than or equal to')
