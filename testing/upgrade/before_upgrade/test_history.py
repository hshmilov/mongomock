import copy
import json
import uuid
from datetime import timedelta, datetime

from axonius.entities import EntityType
from services.axonius_service import AxoniusService
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import History

SAMPLE_DOC = '''
{
    "internal_axon_id" : "e3c7b4d6a159450484ade4560ba044c0",
    "adapter_list_length" : 1,
    "generic_data" : [],
    "specific_data" : [ 
        {
            "client_used" : "1",
            "plugin_type" : "Adapter",
            "plugin_name" : "json_file_adapter",
            "plugin_unique_name" : "json_file_adapter_0",
            "type" : "entitydata",
            "data" : {
                "id" : "cb_id1",
                "name" : "CB 1",
                "hostname" : "CB First",
                "network_interfaces" : [ 
                    {
                        "mac" : "06:3A:9B:D7:D7:A8",
                        "ips" : [ 
                            "10.0.2.1", 
                            "10.0.2.2", 
                            "10.0.2.3"
                        ]
                    }
                ],
                "av_status" : "active",
                "last_contact" : "-",
                "sensor_version" : "0.4.1",
                "test_alert_change" : 5,
                "pretty_id" : "AX-86",
                "adapter_properties" : []
            }
        }
    ],
    "adapters" : [ 
        "json_file_adapter"
    ],
    "labels" : [],
    "short_axon_id" : "e"
}'''


def generate_fake_history(axonius: AxoniusService, entity_type, days, items_per_day):
    history_db = axonius.db.client['aggregator'][f'historical_{entity_type}_db_view']

    entity = json.loads(SAMPLE_DOC)
    entity.pop('_id', None)
    date = datetime.now()

    for day in range(1, days + 1):
        day_entities = []
        for item_num in range(0, items_per_day):
            entity['internal_axon_id'] = uuid.uuid4().hex
            entity['fake_field'] = f'{day}-{item_num}'
            entity['accurate_for_datetime'] = date - timedelta(day)
            entity.pop('_id', None)
            day_entities.append(copy.deepcopy(entity))
        history_db.insert_many(day_entities)

        print(f'history: {entity_type} day {day} done')


class TestPopulateHistory(TestBase):
    def test_populate_history(self):
        generate_fake_history(self.axonius_system, EntityType.Devices.value, days=History.history_depth,
                              items_per_day=History.entities_per_day)
        generate_fake_history(self.axonius_system, EntityType.Users.value, days=History.history_depth,
                              items_per_day=History.entities_per_day)
