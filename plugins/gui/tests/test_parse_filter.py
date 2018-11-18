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
                                     'data._old': {
                                         '$ne': True
                                     }
                                 },
                                 {
                                     '$or': [
                                         {
                                             'data.id': 'c-0'
                                         }
                                     ]
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
                                     'data._old': {
                                         '$ne': True
                                     }
                                 },
                                 {
                                     '$or': [
                                         {
                                             'data.description': {
                                                 '$options': 'i',
                                                 '$regex': 's'
                                             }
                                         }
                                     ]
                                 }
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
                                             'data._old': {
                                                 '$ne': True
                                             }
                                         },
                                         {
                                             '$or': [
                                                 {
                                                     'data.id': 'c-0'
                                                 }
                                             ]
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
                                             'data._old': {
                                                 '$ne': True
                                             }
                                         },
                                         {
                                             '$or': [
                                                 {
                                                     'data.id': 'b'
                                                 }
                                             ]
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
                    'adapters_data': {
                        '$elemMatch': {
                            '$and': [
                                {
                                    'stresstest_adapter._old': {
                                        '$ne': True
                                    }
                                },
                                {
                                    '$or': [
                                        {
                                            'stresstest_adapter.id': 'a'
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                {
                    'adapters_data': {
                        '$elemMatch': {
                            '$and': [
                                {
                                    'stresstest_adapter._old': {
                                        '$ne': True
                                    }
                                },
                                {
                                    '$or': [
                                        {
                                            'stresstest_adapter.id': 'b'
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            ]
        }
    )
