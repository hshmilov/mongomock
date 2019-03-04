{
    'test_hyperlinks_str': function (value) {
        return {
            'type': 'link',
            'href': 'http://test_hyperlinks_str_' + value
        }
    },
    'test_hyperlinks_int': function (value) {
        return {
            'type': 'link',
            'href': 'http://test_hyperlinks_int_' + value
        }
    },
    'test2_hyperlinks_str': function (value) {
        return {
            'type': 'query',
            'module': 'devices',
            'filter': 'test2_hyperlinks_str_' + value
        }
    },
    'test2_hyperlinks_int': function (value) {
        return {
            'type': 'query',
            'module': 'devices',
            'filter': 'adapters_data.stresstest_adapter.test2_hyperlinks_int == ' + value
        }
    }
}