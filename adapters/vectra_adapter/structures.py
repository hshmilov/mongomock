from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field


# pylint: disable=too-many-instance-attributes
class VectraInstance(DeviceAdapter):
    c_score = Field(int, 'Certainty score')
    c_score_gte = Field(int, 'Greater Certainty Score',
                        description='Certainty score greater than or equal to')
    fields = Field(str, 'Filtered Fields',
                   description='Filtered fields in return object')
    is_key_asset = Field(bool, 'Is Key Asset',
                         description='Is device key asset')
    ordering = Field(str, 'Ordering Response Fields',
                     description='Field to use for ordering response')
    page = Field(int, 'Pages Number',
                 description='Number of page to return')
    page_size = Field(int, 'Objects Per Page',
                      description='Number of objects per page or all')
    state = Field(str, 'State')
    t_score = Field(int, 'Threat score')
    t_score_gte = Field(int, 'Greater Threat Score',
                        description='Threat score greater than or equal to')
