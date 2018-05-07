from test_helpers.file_mock_credentials import FileForCredentialsMock

client_details = {
    "user_id": "user",
    # an array of char
    "csv": FileForCredentialsMock("csv_name",
                                  b'Name,Serial,OS,MAC Address,Office\nJohn,Serial2,Windows,11:22:22:33:11:33,Office\nJames,Serial3,Linux,11:22:22:33:11:33,Office')
}

SOME_DEVICE_ID = 'Serial2'
