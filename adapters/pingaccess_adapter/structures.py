import datetime

from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter


class PingaccessUserInstance(UserAdapter):
    device_count = Field(int, 'Device Count')
    device_type = Field(str, 'Device Type')
    device_model = Field(str, 'Device Model')
    device_role = Field(str, 'Device Role')
    os_version = Field(str, 'OS Version')
    last_trx_time = Field(datetime.datetime, 'Last TRX Time')
    country_code = Field(str, 'Country Code')
    device_pairing_date = Field(datetime.datetime, 'Device Pairing Date')
    app_version = Field(str, 'App Version')
