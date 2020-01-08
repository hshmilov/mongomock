DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 1000000

SCROLL_TIMEOUT = 120000

BODY_PARAM_SEARCH = {
    'filters': [
        {
            'filters': [
                {
                    'field': 'inventoryState',
                    'value': 'Confirmed',
                    'type': 'EQ'
                }
            ]
        },
        {
            'filters': [
                {
                    'field': 'assetType',
                    'value': 'WEB_SITE',
                    'type': 'EQ'
                }
            ]
        }
    ]
}
