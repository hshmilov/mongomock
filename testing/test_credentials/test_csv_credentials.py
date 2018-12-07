from test_helpers.file_mock_credentials import FileForCredentialsMock

CSV_FIELDS = [
    'Name',
    'Serial',
    'OS',
    'MAC Address',
    'Office',
]
client_details = {
    "user_id": "user",
    # an array of char
    "csv": FileForCredentialsMock("csv_name",
                                  ','.join(CSV_FIELDS) + '\nJohn,Serial2,Windows,11:22:22:33:11:33,Office\nJames,Serial3,Linux,11:22:22:33:11:33,Office')
}

SOME_DEVICE_ID = 'Serial2'
