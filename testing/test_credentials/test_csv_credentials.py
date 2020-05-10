from test_helpers.file_mock_credentials import FileForCredentialsMock


def create_csv_string(fields: list, data: list):
    """
    create a string representing a csv file
    all field names separated by ',' + line break + all rows data separated with line break
    the row data also separated by ','
    example: given data -> fields['Name', 'Email'] data[['avidor', 'avidor@axonius.com'],['yuval', 'yuval@axonius.com']]
    string result - > 'Name,Email(\n)avidor,avidor@axonius.com(\n)yuval,yuval@axonius.com'
    in table view ->
    Name        Email
    ---------------------------------
    avidor      avidor@axonius.com
    yuval       yuval@axonius.com

    :param fields: the columns names
    :param data: the data of the file
    :return:
    """
    return ','.join(fields) + '\n' + '\n'.join(list(map(lambda x: ','.join(x), data)))


CSV_FIELDS = [
    'Name',
    'Serial',
    'OS',
    'MAC Address',
    'Office',
    'Last Seen',
    'IP'
]
USERS_CSV_FIELDS = [
    'User Name',
    'Email'
]
USERS_CSV_DATA = [
    [
        ['avidor', 'avidor@axonius.com'],
        ['tal', 'tal@axonius.com'],
        ['ron', 'ron@axonius.com']
    ],
    [
        ['avidor', 'avidor@axonius.com'],
        ['yuval', 'yuval@axonius.com']
    ],
    [
        ['avidor', 'avidor@axonius.com'],
        ['hanan', 'hanan@axonius.com']
    ]
]

CSV_LIST = [
    {
        'name': 'John',
        'csv_Serial': 'Serial1',
        'csv_OS': 'Windows',
        'csv_MAC_Address': '11:22:22:33:11:33',
        'csv_Office': 'Office',
        'csv_Last_Seen': '2020-01-03 02:13:24.485Z',
        'csv_IP': '127.0.0.2'
    },
    {
        'name': 'John',
        'csv_Serial': 'Serial2',
        'csv_OS': 'Windows',
        'csv_MAC_Address': '11:22:22:33:11:33',
        'csv_Office': 'Office',
        'csv_Last_Seen': '2020-04-01 02:13:24.485Z',
        'csv_IP': '127.0.0.2'
    },
    {
        'name': 'James',
        'csv_Serial': 'Serial3',
        'csv_OS': 'Linux',
        'csv_MAC_Address': '11:22:22:33:11:33',
        'csv_Office': 'Office',
        'csv_Last_Seen': '2020-01-03 02:13:24.485Z',
    }
]


def list_dict_to_csv(csv_list):
    return '\n'.join([','.join(row.values()) for row in csv_list])


client_details = {
    'user_id': 'user',
    # an array of char
    'file_path': FileForCredentialsMock(
        'csv_name',
        ','.join(CSV_FIELDS) + '\n' + list_dict_to_csv(CSV_LIST))
}

USERS_CLIENT_FILES = [
    {
        'users_1': FileForCredentialsMock(
            'users_1',
            create_csv_string(USERS_CSV_FIELDS, USERS_CSV_DATA[0])
        )
    },
    {
        'users_2': FileForCredentialsMock(
            'users_2',
            create_csv_string(USERS_CSV_FIELDS, USERS_CSV_DATA[1])
        )
    },
    {
        'users_3': FileForCredentialsMock(
            'users_3',
            create_csv_string(USERS_CSV_FIELDS, USERS_CSV_DATA[2])
        )
    }
]

SOME_DEVICE_ID = 'user_Serial2'
