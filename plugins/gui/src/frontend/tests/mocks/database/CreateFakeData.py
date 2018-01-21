from pymongo import MongoClient
import uuid
import random
from datetime import datetime, timedelta
import names
import codenamize

from axonius.device import IPS_FIELD, OS_FIELD

"""
blocked_qcore_num = 40
regular_qcore_num = 4978
ad_esx_splunk_num = 16387
esx_num = 13124
splunk_qcore_num = 1222
"""
blocked_qcore_num = 7
regular_qcore_num = 505
ad_esx_splunk_num = 9822
esx_num = 14967
splunk_qcore_num = 324

DB_HOST = '192.168.127.128'
DB_USER = 'axonAdmin'
DB_PASSWORD = 'Password1'


general_schema = {'internal_axon_id': "{axon_id}",
                  'accurate_for_datetime': "{date_general}",
                  'adapters': {},
                  'tags': []}

adapter_schema = {"client_used": "WIN-0HI4F5QHV2T",
                  "plugin_type": "Adapter",
                  "plugin_name": "{adapter_type}",
                  "unique_plugin_name": "{adapter_type}_1",
                  "accurate_for_datetime": "{date_adapter}",
                  "data": {}}

general_adapter = {"os": "{OS}",
                   "ip": "{IP}",
                   "name": "{name}",
                   "pretty_id": "{pretty_name}",
                   "raw": "relevant?"}


def generate_general():
    g = {}
    g['internal_axon_id'] = uuid.uuid4().hex
    # Generate 20% more than 48 hours, and 80% under
    num = random.random()
    if num > 0.2:
        rand_date = datetime.now() - timedelta(seconds=random.randint(0, 59),
                                               minutes=random.randint(0, 59),
                                               hours=random.randint(0, 3))
    else:
        rand_date = datetime.now() - timedelta(seconds=random.randint(0, 59),
                                               minutes=random.randint(0, 59),
                                               hours=random.randint(24, 60))
    g['accurate_for_datetime'] = str(rand_date)

    g['tags'] = {}
    g['adapters'] = {}
    return g


def generate_adapter_basic(adapter_name, adapter_before=None, os_list=[]):
    g = {}

    if not adapter_before:
        adapter_before_data = dict()
    else:
        adapter_before_data = adapter_before['data']

    g[OS_FIELD] = adapter_before_data.get(
        OS_FIELD, {'type': os_list[random.randint(0, len(os_list) - 1)]})

    g['name'] = adapter_before_data.get('name', names.get_first_name() + "-PC")

    g[IPS_FIELD] = adapter_before_data.get(
        IPS_FIELD, "10.0." + str(random.randint(0, 255)) + "." + str(random.randint(0, 255)))

    g['pretty_id'] = codenamize.codenamize(
        f"{adapter_name}->{uuid.uuid4().hex}", adjectives=1, max_item_chars=6)
    g['pretty_id'] = 'Axon-' + g['pretty_id']

    return g


def generate_adapter(adapter_name, date, client_used, adapter_before=None, os_list=[], **kwargs):
    g = {"client_used": client_used, "plugin_type": "Adapter"}

    g['plugin_name'] = adapter_name
    g['unique_plugin_name'] = adapter_name + '_1'
    g['accurate_for_datetime'] = date

    g['_id'] = uuid.uuid4().hex

    g['data'] = generate_adapter_basic(adapter_name, adapter_before, os_list)
    g['data']['raw'] = globals()["generate_" + adapter_name](**kwargs)

    return g


def generate_ad_adapter():
    return {}


def generate_esx_adapter():
    return {}


def generate_checkpoint_adapter(**kwargs):
    return {'status': kwargs['status']}


def generate_qcore_adapter():
    return {'CQdpmPumpInfo': 'STABLE',
            'CInfuserInfo':  'STABLE',
            'CResourceInfo': 'OK',
            'CDeviceVersion': '1.' + str(random.randint(0, 3)),
            'CQdpmClinicalStatus2': str(random.randint(0, 10)),
            'EQdmClinicalEven': str(random.randint(0, 10)),
            'EQdmPowerStat': str(random.randint(0, 10)),
            'EQdmPowerSourc': str(random.randint(0, 10)),
            'EQdmBatteryStatu': str(random.randint(0, 10)),
            'EAlarmStateTyp': str(random.randint(0, 10))}


def generate_splunk_adapter(**kwargs):
    if kwargs['reporter'] == 'q-core device':
        return {'report_issuer': kwargs['reporter'],
                'CQdpmPumpInfo': 'WARNING',
                'CInfuserInfo':  'STABLE',
                'CResourceInfo': 'OK',
                'CDeviceVersion': '1.' + str(random.randint(0, 3)),
                'CQdpmClinicalStatus2': str(random.randint(0, 10)),
                'EQdmClinicalEven': str(random.randint(0, 10)),
                'EQdmPowerStat': str(random.randint(0, 10)),
                'EQdmPowerSourc': str(random.randint(0, 10)),
                'EQdmBatteryStatu': str(random.randint(0, 10)),
                'EAlarmStateTyp': str(random.randint(0, 10))}
    else:
        return {'report_issuer': kwargs['reporter']}


connection = MongoClient(DB_HOST, username=DB_USER, password=DB_PASSWORD)

##################################### Creating devices ###############################################

loop_count = 0
# Create qcore blocked devices
os_list = ['Embedded']
for i in range(1, blocked_qcore_num):
    print(loop_count)
    loop_count += 1
    g_general = generate_general()
    g_general['adapters']['qcore_adapter'] = generate_adapter('qcore_adapter',
                                                              g_general['accurate_for_datetime'],
                                                              'qcore_admin',
                                                              os_list=os_list)
    g_general['adapters']['checkpoint_adapter'] = generate_adapter('checkpoint_adapter',
                                                                   g_general['accurate_for_datetime'],
                                                                   'checkpoint_controller',
                                                                   adapter_before=g_general['adapters']['qcore_adapter'],
                                                                   os_list=os_list,
                                                                   status='Blocked')

    del g_general['adapters']['qcore_adapter']['data']['name']
    del g_general['adapters']['checkpoint_adapter']['data']['name']
    del g_general['adapters']['checkpoint_adapter']['data']['os']

    connection['aggregator_plugin']['devices_db_2'].insert_one(g_general)

# Create qcore devices
os_list = ['Embedded']
for i in range(1, regular_qcore_num):
    print(loop_count)
    loop_count += 1
    g_general = generate_general()
    g_general['adapters']['qcore_adapter'] = generate_adapter('qcore_adapter',
                                                              g_general['accurate_for_datetime'],
                                                              'qcore_admin',
                                                              os_list=os_list)

    del g_general['adapters']['qcore_adapter']['data']['name']

    connection['aggregator_plugin']['devices_db_2'].insert_one(g_general)


# Create AD + ESX + splunk devices
os_list = ['Microsoft Windows 10 Pro', 'Microsoft Windows 7 Home', 'Microsoft Windows 8.1 Pro',
           'Microsoft Windows 8.1 Home', 'Microsoft Windows 10 Home']
for i in range(1, ad_esx_splunk_num):
    print(loop_count)
    loop_count += 1
    g_general = generate_general()
    g_general['adapters']['ad_adapter'] = generate_adapter('ad_adapter',
                                                           g_general['accurate_for_datetime'],
                                                           "WIN-0HI4F5QHV2T",
                                                           os_list=os_list)

    g_general['adapters']['esx_adapter'] = generate_adapter('esx_adapter',
                                                            g_general['accurate_for_datetime'],
                                                            "esx_main_manage",
                                                            os_list=os_list,
                                                            adapter_before=g_general['adapters']['ad_adapter'])

    g_general['adapters']['splunk_adapter'] = generate_adapter('splunk_adapter',
                                                               g_general['accurate_for_datetime'],
                                                               "splunk_admin",
                                                               os_list=os_list,
                                                               adapter_before=g_general['adapters']['ad_adapter'],
                                                               reporter='active_directory')

    connection['aggregator_plugin']['devices_db_2'].insert_one(g_general)

# Create only ESX devices
os_list = ['Microsoft Windows 10 Pro', 'Microsoft Windows 7 Home', 'Microsoft Windows 8.1 Pro',
           'Microsoft Windows 8.1 Home', 'Microsoft Windows 10 Home', 'Ubuntu 17.10', 'UBUNTU_5', 'Ubuntu 16.04.1 LTS',
           'Ubuntu 14.04.4 LTS', 'macOS 10.13', 'macOs 10.11']
for i in range(1, esx_num):
    print(loop_count)
    loop_count += 1
    g_general = generate_general()

    g_general['adapters']['esx_adapter'] = generate_adapter('esx_adapter',
                                                            g_general['accurate_for_datetime'],
                                                            "esx_main_manage",
                                                            os_list=os_list)

    connection['aggregator_plugin']['devices_db_2'].insert_one(g_general)

# Create only SPLUNK(qcore) devices
os_list = ['Embedded']
for i in range(1, splunk_qcore_num):
    print(loop_count)
    loop_count += 1
    g_general = generate_general()

    g_general['adapters']['splunk_adapter'] = generate_adapter('splunk_adapter',
                                                               g_general['accurate_for_datetime'],
                                                               "splunk_admin",
                                                               os_list=os_list,
                                                               reporter='q-core device')

    del g_general['adapters']['splunk_adapter']['data']['name']

    connection['aggregator_plugin']['devices_db_2'].insert_one(g_general)
