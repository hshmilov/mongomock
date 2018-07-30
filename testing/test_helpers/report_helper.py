from datetime import datetime
from bson.objectid import ObjectId


def get_alert_dict(query_name, report_name):
    return {
        '_id': ObjectId(report_name),
        'report_creation_time': datetime.now(),
        'triggers': {
            'increase': False,
            'decrease': False,
            'no_change': True,
            'above': 0,
            'below': 0
        },
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
            'triggers': {'increase': False, 'decrease': False, 'no_change': False, 'above': 0, 'below': 0},
            'actions': [{'type': 'create_notification'}], 'view': query_name, 'viewEntity': 'devices',
            'retrigger': True, 'triggered': False, 'severity': 'info'}
