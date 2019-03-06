from adapters.json_file_adapter.service import DEVICES_DATA, USERS_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock

USER_NAME_UNICODE = 'אבידור'
DEVICE_FIRST_IP = '10.0.2.1'
DEVICE_SECOND_IP = '10.0.2.2'
DEVICE_THIRD_IP = '10.0.2.3'
DEVICE_MAC = '06:3A:9B:D7:D7:A8'
DEVICE_SUBNET = '10.0.2.0/24'
DEVICE_FIRST_VLAN_NAME = 'vlan0'
DEVICE_SECOND_VLAN_NAME = 'vlan1'
DEVICE_FIRST_VLAN_TAGID = '1'

client_details = {
    DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, '''
    {
        "devices" : [
            {
            "id": "cb_id1",
            "name": "CB 1",
            "hostname": "CB First",
            "network_interfaces": [{
                "mac": "''' + DEVICE_MAC + '''",
                "ips": ["''' + DEVICE_FIRST_IP + '''", "''' + DEVICE_SECOND_IP + '''"],
                "ips_raw": [167772673, 167772674],
                "subnets": ["''' + DEVICE_SUBNET + '''"],
                "vlan_list": [{
                    "name": "''' + DEVICE_FIRST_VLAN_NAME + '''", "tagid": ''' + DEVICE_FIRST_VLAN_TAGID + '''
                }, {
                    "name": "''' + DEVICE_SECOND_VLAN_NAME + '''", "tagid": 2
                }]
            }, {
                "ips": ["''' + DEVICE_THIRD_IP + '''"]
            }],
            "av_status": "active",
            "last_contact": "-",
            "sensor_version": "0.4.1",
            "test_enforcement_change" : 5
            }
        ],
       "fields" : ["id", "network_interfaces", "av_status", "last_contact", "sensor_version", "name", "hostname", 
                   "test_enforcement_change"],
       "additional_schema" : [
            {"name": "av_status", "title": "AvStatus", "type": "string"},
            {"name": "last_contact", "title": "Last Contact", "type": "string"},
            {"name": "sensor_version", "title": "Sensor Version", "type": "string"},
            {"name": "test_enforcement_change", "title": "Test Enforcement Change", "type": "integer"}
        ],
       "raw_fields" : []
    }
    '''),
    USERS_DATA: FileForCredentialsMock(USERS_DATA, '''
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
                },
                {
                "id": "avidor@TestDomain.test",
                "username": "''' + USER_NAME_UNICODE + '''",
                "domain": "TestDomain.test",
                "is_admin": false,
                "mail": "avidor@axonius.com",
                "last_seen": "2018-05-11 02:13:24.485Z",
                "last_password_change": "2017-05-11 02:13:24.485Z"
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
