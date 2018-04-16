from json_file_adapter.service import DATA

client_details = {
    DATA: list(b'''
    {
       "devices" : [
           {"id": "cb_id1",
            "network_interfaces": [{"mac": "06:3A:9B:D7:D7:A8", "ips": ["10.0.2.1"]}],
            "av_status": "active",
            "last_contact": "-",
            "sensor_version": "0.4.1"
           }
           ],
       "fields" : ["id", "av_status", "last_contact", "sensor_version", "name", "hostname"],
       "additional_schema" : [{"name": "av_status", "title": "AvStatus", "type": "string"}],
       "raw_fields" : []
    }
    ''')
}

SOME_DEVICE_ID = 'cb_id1'
