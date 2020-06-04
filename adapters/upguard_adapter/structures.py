import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter


class BreachData(SmartJsonClass):
    name = Field(str, 'Name')
    title = Field(str, 'Title')
    domain = Field(str, 'Domain')
    description = Field(str, 'Description')
    date_occurred = Field(datetime.datetime, 'Date Occurred')
    exposed_data_classes = ListField(str, 'Exposed Data Classes')
    total_exposures = Field(int, 'Total Exposures')


class UpguardUserInstance(UserAdapter):
    last_breach_date = Field(datetime.datetime, 'Last Breach Date')
    num_breaches = Field(int, 'Number Of Breaches')
    breaches_data = ListField(BreachData, 'Breaches')
