from adapters.json_file_adapter.service import DEVICES_DATA, USERS_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock

client_details = {
    DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, b'''
    {
        "devices" : [
            {
            "id": "cb_id1",
            "name": "CB 1",
            "hostname": "CB First",
            "network_interfaces": [{"mac": "06:3A:9B:D7:D7:A8", "ips": ["10.0.2.1"]}],
            "av_status": "active",
            "last_contact": "-",
            "sensor_version": "0.4.1"
            }
        ],
       "fields" : ["id", "network_interfaces", "av_status", "last_contact", "sensor_version", "name", "hostname"],
       "additional_schema" : [
            {"name": "av_status", "title": "AvStatus", "type": "string"},
            {"name": "last_contact", "title": "Last Contact", "type": "string"},
            {"name": "sensor_version", "title": "Sensor Version", "type": "string"}
        ],
       "raw_fields" : []
    }
    '''),
    USERS_DATA: FileForCredentialsMock(USERS_DATA, b'''
        {
            "users" : [
                {
                "id": "ofri@TestDomain.test",
                "username": "ofri",
                "domain": "TestDomain.test",
                "is_admin": true,
                "mail": "ofri@axonius.com",
                "last_seen": "2018-04-11 02:13:24.485Z",
                "last_password_change": "2017-04-11 02:13:24.485Z"
                }
            ],
            "fields" : ["id", "username", "domain", "is_admin", "last_seen", "mail"],
            "additional_schema" : [
                {
                "name": "last_password_change", "title": "Password Last Changed On",
                "type": "string", "format": "date-time"
                }
            ],
            "raw_fields" : []
        }
        ''')
}

SOME_DEVICE_ID = 'cb_id1'
