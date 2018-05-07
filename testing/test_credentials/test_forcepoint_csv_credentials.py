from test_helpers.file_mock_credentials import FileForCredentialsMock

client_details = {
    "user_id": "user",
    "csv": FileForCredentialsMock("csv_name",
                                  b'Hostname,IP Address,Logged-in Users,Last Update,Profile Name,Synced,Discovery Status,Client Status,'
                                  b'Client Installation Version\nmyhost,"172.16.0.103,10.1.1.145",domain\user,'
                                  b'3/10/2052 11:09,Default Profile,FALSE,Idle,Enabled,8.1.2252')
}

SOME_DEVICE_ID = 'myhost'
