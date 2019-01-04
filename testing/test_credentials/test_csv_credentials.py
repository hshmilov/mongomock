from test_helpers.file_mock_credentials import FileForCredentialsMock

CSV_FIELDS = [
    'Name',
    'Serial',
    'OS',
    'MAC Address',
    'Office',
    'Last Seen',
    'IP'
]
client_details = {
    "user_id": "user",
    # an array of char
    "csv": FileForCredentialsMock("csv_name",
                                  ','.join(CSV_FIELDS) + '\nJohn,Serial1,Windows,11:22:22:33:11:33,Office,2018-04-11 02:13:24.485Z, 127.0.0.1\nJohn,Serial2,Windows,11:22:22:33:11:33,Office,2019-01-01 02:13:24.485Z, 127.0.0.1\nJames,Serial3,Linux,11:22:22:33:11:33,Office,2018-04-11 02:13:24.485Z')
}

SOME_DEVICE_ID = 'Serial2'
