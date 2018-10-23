from datetime import datetime
from bson.objectid import ObjectId
from axonius.consts.report_consts import TRIGGERS_DEFAULT_VALUES


def get_alert_dict(query_name, report_name):
    triggers_dict = TRIGGERS_DEFAULT_VALUES
    triggers_dict['every_discovery'] = True
    return {
        '_id': ObjectId(report_name),
        'report_creation_time': datetime.now(),
        'triggers': triggers_dict,
        'actions': [
            {
                'type': 'create_notification'
            }
        ],
        'result': [
        ],
        'view': query_name,
        'view_entity': 'devices',
        'retrigger': True,
        'triggered': 0,
        'name': report_name,
        'severity': 'info'
    }


def create_alert_dict(query_name, report_name):
    return {'id': 'new', 'name': report_name,
            'triggers': TRIGGERS_DEFAULT_VALUES,
            'actions': [{'type': 'create_notification'}], 'view': query_name, 'viewEntity': 'devices',
            'retrigger': True, 'triggered': False, 'severity': 'info'}
