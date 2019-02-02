from axonius.utils.parsing import parse_filter


def assert_equal(axonius_query: str, mongo_dict: dict):
    result = parse_filter(axonius_query)
    print(f'{axonius_query} -> {mongo_dict}, got {result}')
    assert result == mongo_dict


# There's no point testing "regular" cases because we have no intention of testing the FQL package
# we actually want to test our own code

def test_basic_no_dups_query():
    assert_equal('specific_data.data.id == "c-0"',
                 {
                     'specific_data': {
                         '$elemMatch': {
                             '$and': [
                                 {
                                     '$or': [
                                         {
                                             'data.id': 'c-0'
                                         }
                                     ]
                                 },
                                 {
                                     'data._old': {
                                         '$ne': True
                                     }
                                 }
                             ]
                         }
                     }
                 }
                 )


def test_regex_no_dups():
    assert_equal('specific_data.data.description == regex("s", "i")',
                 {
                     'specific_data': {
                         '$elemMatch': {
                             '$and': [
                                 {
                                     '$or': [
                                         {
                                             'data.description': {
                                                 '$options': 'i',
                                                 '$regex': 's'
                                             }
                                         }
                                     ]
                                 },
                                 {
                                     'data._old': {
                                         '$ne': True
                                     }
                                 },
                             ]
                         }
                     }
                 }
                 )


def test_and_no_dups():
    assert_equal('specific_data.data.id == "c-0" and specific_data.data.id == "b"',
                 {
                     '$and': [
                         {
                             'specific_data': {
                                 '$elemMatch': {
                                     '$and': [
                                         {
                                             '$or': [
                                                 {
                                                     'data.id': 'c-0'
                                                 }
                                             ]
                                         },
                                         {
                                             'data._old': {
                                                 '$ne': True
                                             }
                                         },
                                     ]
                                 }
                             }
                         },
                         {
                             'specific_data': {
                                 '$elemMatch': {
                                     '$and': [
                                         {
                                             '$or': [
                                                 {
                                                     'data.id': 'b'
                                                 }
                                             ]
                                         },
                                         {
                                             'data._old': {
                                                 '$ne': True
                                             }
                                         }
                                     ]
                                 }
                             }
                         }
                     ]
                 }
                 )


def test_and_no_dups_adpater_data():
    assert_equal(
        'adapters_data.stresstest_adapter.id == "a" and adapters_data.stresstest_adapter.id == "b"',
        {
            '$and': [
                {
                    'specific_data': {
                        '$elemMatch': {
                            '$and': [
                                {
                                    'plugin_name': 'stresstest_adapter'
                                },
                                {
                                    '$or': [
                                        {
                                            'data.id': 'a'
                                        }
                                    ]
                                },
                                {
                                    'data._old': {
                                        '$ne': True
                                    }
                                }
                            ]
                        }
                    }
                },
                {
                    'specific_data': {
                        '$elemMatch': {
                            '$and': [
                                {
                                    'plugin_name': 'stresstest_adapter'
                                },
                                {
                                    '$or': [
                                        {
                                            'data.id': 'b'
                                        }
                                    ]
                                },
                                {
                                    'data._old': {
                                        '$ne': True
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
        }
    )
