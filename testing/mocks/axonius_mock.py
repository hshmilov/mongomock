import random
from datetime import datetime, timedelta

from mongomock import MongoClient, ObjectId

from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon


class AxoniusMock(AxoniusCommon):
    MANAGED_DEVICES_VIEW_ID = '5f884556801d4d16e58da7a1'
    RECENTLY_SEEN_VIEW_ID = '5f884556801d4d16e58da792'
    IPS_VIEW_ID = '5f8aaf31e23bca37d2fdb540'
    WINDOWS_VIEW_ID = '5f8adbb3e23bca37d2fe83ce'
    HOSTNAMES_VIEW_ID = '5fa037a3194c982463a90b79'

    HOST_NAMES = ['TESTWINDOWS7.TestDomain.test',
                  '22AD.TestDomain.test',
                  'dc1.TestDomain.test',
                  'Computer-next-to-printer.TestDomain.test']

    def __init__(self):
        super().__init__(MongoClient())

    def prepare_default(self):
        self.insert_default_devices()
        self.insert_default_devices_history()
        self.insert_default_device_views()

    def insert_default_devices(self):
        self.data.entity_data_collection[EntityType.Devices].insert_many([{
            'internal_axon_id': '0f796e89e9d57cebfb887b2cb6a66f35',
            'accurate_for_datetime': '2020-10-16T01:44:32.675Z',
            'adapters': [{
                'client_used': 'TestDomain.test',
                'plugin_type': 'Adapter',
                'plugin_name': 'active_directory_adapter',
                'plugin_unique_name': 'active_directory_adapter_0',
                'type': 'entitydata',
                'accurate_for_datetime': '2020-10-15T15:22:19.556Z',
                'data': {
                    'id': 'CN=TESTWINDOWS7,CN=Computers,DC=TestDomain,DC=test',
                    'hostname': self.HOST_NAMES[0],
                    'name': 'TESTWINDOWS7',
                    'last_seen': self._generate_last_seen(10),
                    'os': {
                        'type': 'Windows',
                        'distribution': '7',
                        'os_str': 'windows 7 ultimate',
                        'is_windows_server': False,
                        'type_distribution': 'Windows 7',
                        'build': '7601',
                        'sp': 'Service Pack 1'
                    },
                    'network_interfaces': [{
                        'ips': ['192.168.20.93'],
                        'ips_v4': ['192.168.20.93'],
                        'subnets': ['192.168.20.0/24']
                    }],
                    'number_of_processes': 2,
                    'adapter_properties': ['Assets', 'Manager']
                }
            }],
            'tags': []
        }, {
            'internal_axon_id': 'a5f257e7f0902fc99082fc73dbb529c9',
            'accurate_for_datetime': '2020-10-16T01:44:32.709Z',
            'adapters': [{
                'client_used': 'TestDomain.test',
                'plugin_type': 'Adapter',
                'plugin_name': 'active_directory_adapter',
                'plugin_unique_name': 'active_directory_adapter_0',
                'type': 'entitydata',
                'accurate_for_datetime': '2020-10-16T01:44:32.709Z',
                'data': {
                    'id': 'CN=22AD,CN=Computers,DC=TestDomain,DC=test',
                    'hostname': self.HOST_NAMES[1],
                    'name': '22AD',
                    'last_seen': self._generate_last_seen(3),
                    'os': {
                        'type': 'Windows',
                        'distribution': 'Server 2012 R2',
                        'os_str': 'windows server 2012 r2 standard',
                        'is_windows_server': True,
                        'type_distribution': 'Windows Server 2012 R2',
                        'build': '9600'
                    },
                    'network_interfaces': [{
                        'ips': ['10.0.227.26'],
                        'ips_v4': ['10.0.227.26'],
                        'subnets': ['10.0.224.0/20']
                    }],
                    'number_of_processes': 4,
                    'adapter_properties': ['Assets', 'Manager']
                }
            }],
            'tags': []
        }, {
            'internal_axon_id': '842ef5b094c6434047eed8e11e49d1f3',
            'accurate_for_datetime': '2020-10-16T01:44:32.723Z',
            'adapters': [{
                'client_used': 'TestDomain.test',
                'plugin_type': 'Adapter',
                'plugin_name': 'active_directory_adapter',
                'plugin_unique_name': 'active_directory_adapter_0',
                'type': 'entitydata',
                'accurate_for_datetime': '2020-10-16T01:44:32.723Z',
                'data': {
                    'id': 'CN=DC1,OU=Domain Controllers,DC=TestDomain,DC=test',
                    'hostname': self.HOST_NAMES[2],
                    'name': 'DC1',
                    'last_seen': self._generate_last_seen(2),
                    'os': {
                        'type': 'Windows',
                        'distribution': 'Server 2016',
                        'os_str': 'windows server 2016 standard',
                        'is_windows_server': True,
                        'type_distribution': 'Windows Server 2016',
                        'build': '14393'
                    },
                    'network_interfaces': [{
                        'ips': ['192.168.20.25'],
                        'ips_v4': ['192.168.20.25'],
                        'subnets': ['192.168.20.0/24']
                    }],
                    'adapter_properties': ['Assets', 'Manager']
                }
            }],
            'tags': []
        }, {
            'internal_axon_id': '75472832285d856be415e103e6318594',
            'accurate_for_datetime': '2020-10-16T01:44:32.697Z',
            'adapters': [{
                'client_used': 'TestDomain.test',
                'plugin_type': 'Adapter',
                'plugin_name': 'active_directory_adapter',
                'plugin_unique_name': 'active_directory_adapter_0',
                'type': 'entitydata',
                'accurate_for_datetime': '2020-10-16T01:44:32.697Z',
                'data': {
                    'id': 'CN=Computer-next-to-printer,OU=משרד,DC=TestDomain,DC=test',
                    'hostname': self.HOST_NAMES[3],
                    'name': 'Computer-next-to-printer',
                    'os': {},
                    'network_interfaces': [],
                    'adapter_properties': ['Assets', 'Manager']
                }
            }],
            'tags': []
        }])

    def insert_default_devices_history(self):
        current_devices = list(self.data.entity_data_collection[EntityType.Devices].find({}, {
            '_id': False
        }))
        for day in range(0, 8):
            history_date = datetime.now() - timedelta(day)
            history_collection_name = f'historical_{EntityType.Devices.value}_{history_date.strftime("%Y_%m_%d")}'
            history_devices = [d for d in current_devices if bool(random.getrandbits(1))]
            if not history_devices:
                self.data.plugins.aggregator.plugin_db.create_collection(history_collection_name)
                continue
            self.data.plugins.aggregator.plugin_db[history_collection_name].insert_many(history_devices)
            for device in history_devices:
                device['accurate_for_datetime'] = history_date
                del device['_id']
            self.data.entity_history_collection[EntityType.Devices].insert_many(history_devices)

    @staticmethod
    def _generate_last_seen(days_ago: int):
        return datetime.now() - timedelta(days=days_ago)

    def insert_default_device_views(self):
        self.data.entity_views_collection[EntityType.Devices].insert_many([{
            '_id': ObjectId(self.MANAGED_DEVICES_VIEW_ID),
            'name': 'Managed Devices',
            'description': 'Devices that have been seen by at least one agent or endpoint management solution.',
            'tags': [
                'Unmanaged Devices'
            ],
            'view': {
                'fields': [
                    'adapters',
                    'specific_data.data.name',
                    'specific_data.data.hostname',
                    'specific_data.data.last_seen',
                    'specific_data.data.network_interfaces.manufacturer',
                    'specific_data.data.network_interfaces.mac',
                    'specific_data.data.network_interfaces.ips',
                    'specific_data.data.os.type',
                    'labels'
                ],
                'coloumnSizes': [],
                'query': {
                    'filter': '(specific_data.data.adapter_properties == \'Agent\') '
                              'or (specific_data.data.adapter_properties == \'Manager\')',
                    'expressions': [
                        {
                            'compOp': 'equals',
                            'field': 'specific_data.data.adapter_properties',
                            'i': 0,
                            'leftBracket': False,
                            'logicOp': '',
                            'not': False,
                            'rightBracket': False,
                            'value': 'Agent',
                            'fieldType': 'axonius'
                        },
                        {
                            'compOp': 'equals',
                            'field': 'specific_data.data.adapter_properties',
                            'i': 1,
                            'leftBracket': False,
                            'logicOp': 'or',
                            'not': False,
                            'rightBracket': False,
                            'value': 'Manager',
                            'fieldType': 'axonius'
                        }
                    ]
                },
                'sort': {
                    'field': '',
                    'desc': True
                }
            },
            'query_type': 'saved',
            'timestamp': '2020-10-17T11:57:51.636Z',
            'user_id': '*',
            'updated_by': '*',
            'predefined': True,
            'private': False
        }, {
            '_id': ObjectId(self.RECENTLY_SEEN_VIEW_ID),
            'name': 'Devices seen in last 7 days',
            'description': 'Devices that have been seen by at least one solution/adapter in the last 7 days.',
            'tags': [
                'Unmanaged Devices'
            ],
            'view': {
                'fields': [
                    'adapters',
                    'specific_data.data.name',
                    'specific_data.data.hostname',
                    'specific_data.data.last_seen',
                    'specific_data.data.network_interfaces.mac',
                    'specific_data.data.network_interfaces.ips',
                    'specific_data.data.os.type',
                    'labels'
                ],
                'coloumnSizes': [],
                'query': {
                    'filter': 'specific_data.data.last_seen >= date(\'NOW - 7d\')',
                    'expressions': [
                        {
                            'compOp': 'days',
                            'field': 'specific_data.data.last_seen',
                            'leftBracket': False,
                            'logicOp': '',
                            'not': False,
                            'rightBracket': False,
                            'value': 7
                        }
                    ]
                },
                'sort': {
                    'field': '',
                    'desc': True
                }
            },
            'query_type': 'saved',
            'timestamp': '2020-10-17T11:57:51.614Z',
            'user_id': '*',
            'updated_by': '*',
            'predefined': True,
            'private': False
        }, {
            '_id': ObjectId(self.IPS_VIEW_ID),
            'name': 'IPs on 192.168',
            'archived': False,
            'description': None,
            'last_updated': '2020-10-17T08:45:37.761Z',
            'private': False,
            'query_type': 'saved',
            'tags': [],
            'updated_by': ObjectId('5f884556625560e1f82fb802'),
            'user_id': ObjectId('5f884556625560e1f82fb802'),
            'view': {
                'query': {
                    'filter': '(specific_data.data.network_interfaces.ips == regex(\'192\\.168\', \'i\'))',
                    'onlyExpressionsFilter': 'specific_data.data.network_interfaces.ips == regex(\'192\\.168\', \'i\')',
                    'expressions': [
                        {
                            'logicOp': '',
                            'not': False,
                            'leftBracket': False,
                            'field': 'specific_data.data.network_interfaces.ips',
                            'compOp': 'contains',
                            'value': '192.168',
                            'rightBracket': False,
                            'children': [
                                {
                                    'expression': {
                                        'field': '',
                                        'compOp': '',
                                        'value': None,
                                        'filteredAdapters': None
                                    },
                                    'condition': '',
                                    'i': 0
                                }
                            ],
                            'fieldType': 'axonius',
                            'filter': '(specific_data.data.network_interfaces.ips == regex(\'192\\.168\', \'i\'))',
                            'bracketWeight': 0
                        }
                    ],
                    'meta': {
                        'uniqueAdapters': False,
                        'enforcementFilter': ''
                    },
                    'search': None
                },
                'fields': [
                    'adapters',
                    'specific_data.data.name',
                    'specific_data.data.hostname',
                    'specific_data.data.last_seen',
                    'specific_data.data.network_interfaces.mac',
                    'specific_data.data.network_interfaces.ips',
                    'specific_data.data.os.type',
                    'labels'
                ],
                'sort': {
                    'field': '',
                    'desc': True
                },
                'colFilters': {},
                'colExcludedAdapters': {}
            }
        }, {
            '_id': ObjectId(self.WINDOWS_VIEW_ID),
            'name': 'Windows',
            'archived': False,
            'description': None,
            'last_updated': '2020-10-17T11:55:31.062Z',
            'private': False,
            'query_type': 'saved',
            'tags': [],
            'updated_by': ObjectId('5f884556625560e1f82fb802'),
            'user_id': ObjectId('5f884556625560e1f82fb802'),
            'view': {
                'query': {
                    'filter': '(specific_data.data.os.type == \'Windows\')',
                    'onlyExpressionsFilter': '(specific_data.data.os.type == \'Windows\')',
                    'expressions': [
                        {
                            'logicOp': '',
                            'not': False,
                            'leftBracket': False,
                            'field': 'specific_data.data.os.type',
                            'compOp': 'equals',
                            'value': 'Windows',
                            'rightBracket': False,
                            'children': [
                                {
                                    'expression': {
                                        'field': '',
                                        'compOp': '',
                                        'value': None,
                                        'filteredAdapters': None
                                    },
                                    'condition': '',
                                    'i': 0
                                }
                            ],
                            'fieldType': 'axonius',
                            'filter': '(specific_data.data.os.type == \'Windows\')',
                            'bracketWeight': 0
                        }
                    ],
                    'meta': {
                        'enforcementFilter': ''
                    },
                    'search': None
                },
                'fields': [
                    'adapters',
                    'specific_data.data.name',
                    'specific_data.data.hostname',
                    'specific_data.data.last_seen',
                    'specific_data.data.network_interfaces.mac',
                    'specific_data.data.network_interfaces.ips',
                    'specific_data.data.os.type',
                    'labels'
                ],
                'sort': {
                    'field': '',
                    'desc': True
                },
                'colFilters': {},
                'colExcludedAdapters': {}
            }
        }, {
            '_id': ObjectId(self.HOSTNAMES_VIEW_ID),
            'name': 'Hostname Whitelist',
            'archived': False,
            'description': None,
            'last_updated': '2020-10-17T11:55:31.062Z',
            'private': False,
            'query_type': 'saved',
            'tags': [],
            'updated_by': ObjectId('5fa017009cc4eb7c448d524a'),
            'user_id': ObjectId('5fa017009cc4eb7c448d524a'),
            'view': {
                'query': {
                    'filter': f'("specific_data.data.hostname" in ["{self.HOST_NAMES[0]}","{self.HOST_NAMES[3]}"])',
                    'expressions': [
                        {
                            'logicOp': '',
                            'not': False,
                            'leftBracket': False,
                            'field': 'specific_data.data.hostname',
                            'compOp': 'IN',
                            'value': 'TESTWINDOWS7.TestDomain.test,Computer-next-to-printer.TestDomain.test',
                            'rightBracket': False,
                            'children': [
                                {
                                    'expression': {
                                        'field': '',
                                        'compOp': '',
                                        'value': None,
                                        'filteredAdapters': None
                                    },
                                    'condition': '',
                                    'i': 0
                                }
                            ],
                            'fieldType': 'axonius',
                            'bracketWeight': 0
                        }
                    ],
                    'meta': {
                        'enforcementFilter': ''
                    },
                    'search': None
                },
                'fields': [
                    'adapters',
                    'specific_data.data.name',
                    'specific_data.data.hostname',
                    'specific_data.data.last_seen',
                    'specific_data.data.network_interfaces.mac',
                    'specific_data.data.network_interfaces.ips',
                    'specific_data.data.os.type',
                    'labels'
                ],
                'sort': {
                    'field': '',
                    'desc': True
                },
                'colFilters': {},
                'colExcludedAdapters': {}
            }
        }])

    def insert_chart(self, chart_doc: dict):
        return self.data.dashboard_collection.insert_one(chart_doc).inserted_id

    def update_chart(self, chart_id: ObjectId, chart_doc: dict):
        self.data.dashboard_collection.update_one({
            '_id': chart_id
        }, {
            '$set': chart_doc
        })
