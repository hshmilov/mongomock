from test_helpers.file_mock_credentials import FileForCredentialsMock

USERS_JSON_DATA = '''[
    {
      "apples": "martini",
      "nuts": "pie",
      "id": "111",
      "email": "one@example.com",
      "username": "one",
      "name": "one zerosson"
    },
    {
      "apples": "juice",
      "nuts": "crackers",
      "id": "222",
      "email": "two@example.com",
      "username": "two",
      "name": "two oneson"
    },
    {
      "apples": "pie",
      "nuts": "sometimes",
      "id": "333",
      "email": "three@example.com",
      "username": "three",
      "name": "three onesdottir"
    }
]'''

DEVICES_JSON_DATA = '''[
    {
        "Name": "John",
        "Serial": "Serial1",
        "OS": "Windows",
        "MAC Address": "11:22:22:33:11:33",
        "Office": "Office",
        "Last Seen": "2020-01-03 02:13:24.485Z",
        "IP": "127.0.0.1"
    },
    {
        "ID": "111",
        "Name": "John",
        "Serial": "Serial2",
        "OS": "Windows XP SP1",
        "MAC Address": "11:22:22:33:11:33",
        "Office": "Office",
        "Last Seen": "2020-04-01 02:13:24.485Z",
        "IP": "127.0.0.1",
        "Packages": [
            "MS Office 365", "Solitaire", "Space Cadet Pinball"
        ]
    }
]'''

JSON_TEST_FIELDS = [
    'Name',
    'Serial',
    'OS',
    'MAC Address',
    'Office',
    'Last Seen',
    'IP'
]

USERS_CLIENT_FILE = FileForCredentialsMock(
    'users_json',
    USERS_JSON_DATA
)


DEVICES_CLIENT_FILE = FileForCredentialsMock(
    'devices_json',
    DEVICES_JSON_DATA)

CLIENT_DETAILS = {
    'user_id': 'devices_json',
    'file_path': DEVICES_CLIENT_FILE
}

SOME_USER_ID = 'users_json_222'

SOME_DEVICE_ID = 'devices_json_111'
