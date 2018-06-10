from test_helpers.file_mock_credentials import FileForCredentialsMock
from datetime import datetime, timedelta

time_to_enter = datetime.now() - timedelta(weeks=1)
time_as_format = f"{time_to_enter.month}/{time_to_enter.day}/{time_to_enter.year}"

client_details = {
    "user_id": "user",
    "csv": FileForCredentialsMock("csv",
                                  f'Endpoint Name,Recording Policy,Version,Status,Installation,Last Activity Date,Last Activity Time,'
                                  f'Status Type,OS Type,OS Version,Last Heartbeat Date,Last Heartbeat Time\r\nWIN-TV9UBKLP1KN,'
                                  f'Default Windows-based Policy,7.4.1.27,OK,{time_as_format},{time_as_format},11:55:22,,'
                                  f'Windows,Windows 8.1,{time_as_format},11:55:26\r\n'.encode("utf-8")),
    "domain": "TESTSECDOMAIN.TEST"
}

SOME_DEVICE_ID = 'WIN-TV9UBKLP1KN.TESTSECDOMAIN.TEST'
