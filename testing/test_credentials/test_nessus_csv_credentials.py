from test_helpers.file_mock_credentials import FileForCredentialsMock

client_details = {
    "user_id": "user",
    "csv": FileForCredentialsMock("csv_name",
                                  b'')
}

SOME_DEVICE_ID = "192.168.20.10"
SOME_DEVICE_IP = "192.168.20.10"
