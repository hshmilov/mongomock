DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

DEFAULT_DOMAIN_ID = 1

FIREMON_API_PREFIX = '/securitymanager/api'

CONTROL_NAME_ENRICH_IOS = 'Axonius_Enrich_IOS_Version'
CONTROL_ENRICH_IOS_DEVICE_TYPE = 'ROUTER_SWITCH'
CONTROL_ENRICH_IOS_DEVICE_VENDOR = 'Cisco'
CONTROL_ENRICH_IOS_DEVICE_NAME = 'IOS'
CONTROL_ENRICH_IOS_DEVICE_FILENAME = 'version'
CONTROL_DETAILS_ENRICH_IOS = {
    'name': CONTROL_NAME_ENRICH_IOS,
    'controlType': 'REGEX',

    'domainId': 1,
    'severity': 1,
    'system': False,

    'properties': [

        # Search All Files - FALSE
        {'controlType': 'REGEX', 'name': 'SearchAllFiles', 'type': 'BOOLEAN', 'required': True,
         'displayName': 'Search All Files', 'booleanValue': False, },

        # define 'version' as filename pattern
        {'controlType': 'REGEX', 'name': 'FilenamesToSearch', 'type': 'STRING', 'required': False,
         'displayName': 'Filenames To Search', 'string': CONTROL_ENRICH_IOS_DEVICE_FILENAME, },

        # define 'RELEASE SOFTWARE' as line pattern
        {'controlType': 'REGEX', 'name': 'Pattern', 'type': 'STRING', 'required': True,
         'displayName': 'Pattern', 'string': 'RELEASE SOFTWARE', },

        # Fail if pattern matches (we will retrieve the failure)
        {'controlType': 'REGEX', 'name': 'FailWhenResultsExist', 'required': True, 'type': 'BOOLEAN',
         'displayName': 'Fail When Results Exist', 'booleanValue': True, },

        # Information only - FALSE
        {'controlType': 'REGEX', 'name': 'InfoOnly', 'type': 'BOOLEAN', 'required': True,
         'displayName': 'Information Only', 'booleanValue': False, },

        # Max Line Length - 160
        {'controlType': 'REGEX', 'name': 'MaxLineLength', 'type': 'INTEGER', 'required': True,
         'displayName': 'Max Line Length', 'integerValue': 160, },
    ],

    'filters': [
        {'type': 'DEVICE_TYPE', 'deviceType': CONTROL_ENRICH_IOS_DEVICE_TYPE, },
        {'type': 'VENDOR', 'vendor': CONTROL_ENRICH_IOS_DEVICE_VENDOR, },
        {'type': 'DEVICE_NAME', 'deviceName': CONTROL_ENRICH_IOS_DEVICE_NAME, },
    ],
}

ASSESSMENT_RESULT_PARAMS = {
    'allControlResults': True,
    'allFailedRules': False,
    'includeDeviceSummary': False,
    'includeSubgroups': False,
}
