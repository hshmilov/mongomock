from axonius.utils.axonius_query_language import parse_filter


# pylint: disable=C0330

def assert_equal(axonius_query: str, mongo_dict: dict):
    result = parse_filter(axonius_query)
    print(f'{axonius_query} -> {mongo_dict}, got {result}')
    assert result == mongo_dict


# There's no point testing "regular" cases because we have no intention of testing the FQL package
# we actually want to test our own code

def test_basic_no_dups_query():
    assert_equal('specific_data.data.id == "c-0"',
                 {'$and': [{'$or': [{'adapters': {'$elemMatch': {'$and': [{'data.id': 'c-0'},
                                                                          {'pending_delete': {'$ne': True}},
                                                                          {'data._old': {'$ne': True}}]}}},
                                    {'tags': {'$elemMatch': {'$and': [{'data.id': 'c-0'},
                                                                      {'pending_delete': {'$ne': True}},
                                                                      {'data._old': {'$ne': True}},
                                                                      {'type': 'adapterdata'}]}}}]}]}
                 )


def test_regex_no_dups():
    assert_equal('specific_data.data.description == regex("s", "i")',
                 {'$and': [{'$or': [{'adapters': {'$elemMatch': {'$and': [{'data.description': {'$options': 'i',
                                                                                                '$regex': 's'}},
                                                                          {'pending_delete': {'$ne': True}},
                                                                          {'data._old': {'$ne': True}}]}}},
                                    {'tags': {'$elemMatch': {'$and': [{'data.description': {'$options': 'i',
                                                                                            '$regex': 's'}},
                                                                      {'pending_delete': {'$ne': True}},
                                                                      {'data._old': {'$ne': True}},
                                                                      {'type': 'adapterdata'}]}}}]}]}
                 )


def test_and_no_dups():
    assert_equal('specific_data.data.id == "c-0" and specific_data.data.id == "b"',
                 {'$and': [{'$and': [{'$or': [{'adapters': {'$elemMatch': {'$and': [{'data.id': 'c-0'},
                                                                                    {'pending_delete': {'$ne': True}},
                                                                                    {'data._old': {'$ne': True}}]}}},
                                              {'tags': {'$elemMatch': {'$and': [{'data.id': 'c-0'},
                                                                                {'pending_delete': {'$ne': True}},
                                                                                {'data._old': {'$ne': True}},
                                                                                {'type': 'adapterdata'}]}}}]},
                                     {'$or': [{'adapters': {'$elemMatch': {'$and': [{'data.id': 'b'},
                                                                                    {'pending_delete': {'$ne': True}},
                                                                                    {'data._old': {'$ne': True}}]}}},
                                              {'tags': {'$elemMatch': {'$and': [{'data.id': 'b'},
                                                                                {'pending_delete': {'$ne': True}},
                                                                                {'data._old': {'$ne': True}},
                                                                                {'type': 'adapterdata'}]}}}]}]}]}
                 )


def test_and_no_dups_adpater_data():
    assert_equal(
        'adapters_data.stresstest_adapter.id == "a" and adapters_data.stresstest_adapter.id == "b"',
        {'$and': [{'$and': [{'$or': [{'adapters': {'$elemMatch': {'$and': [{'plugin_name': 'stresstest_adapter'},
                                                                           {'pending_delete': {'$ne': True}},
                                                                           {'data.id': 'a'},
                                                                           {'data._old': {'$ne': True}}]}}},
                                     {'tags': {'$elemMatch': {'$and': [{'plugin_name': 'stresstest_adapter'},
                                                                       {'pending_delete': {'$ne': True}},
                                                                       {'data.id': 'a'},
                                                                       {'data._old': {'$ne': True}},
                                                                       {'type': 'adapterdata'}]}}}]},
                            {'$or': [{'adapters': {'$elemMatch': {'$and': [{'plugin_name': 'stresstest_adapter'},
                                                                           {'pending_delete': {'$ne': True}},
                                                                           {'data.id': 'b'},
                                                                           {'data._old': {'$ne': True}}]}}},
                                     {'tags': {'$elemMatch': {'$and': [{'plugin_name': 'stresstest_adapter'},
                                                                       {'pending_delete': {'$ne': True}},
                                                                       {'data.id': 'b'},
                                                                       {'data._old': {'$ne': True}},
                                                                       {'type': 'adapterdata'}]}}}]}]}]}
    )


def test_match_specific():
    assert_equal(
        'specific_data.data.network_interfaces == match([mac == "1"])',
        {'$and': [
            {'$or': [{'adapters': {'$elemMatch': {'$and': [{'data.network_interfaces': {'$elemMatch': {'mac': '1'}}},
                                                           {'pending_delete': {'$ne': True}},
                                                           {'data._old': {'$ne': True}}]}}},
                     {'tags': {'$elemMatch': {'$and': [{'data.network_interfaces': {'$elemMatch': {'mac': '1'}}},
                                                       {'pending_delete': {'$ne': True}},
                                                       {'data._old': {'$ne': True}},
                                                       {'type': 'adapterdata'}]}}}]}]}
    )


def test_match_adapters():
    assert_equal('adapters_data.cisco_prime_adapter.network_interfaces == match([mac == "2" and manufacturer == "4"])',
                 {'$and': [{'$or': [{'adapters': {'$elemMatch': {'$and': [{'plugin_name': 'cisco_prime_adapter'},
                                                                          {'pending_delete': {'$ne': True}},
                                                                          {'data.network_interfaces': {
                                                                              '$elemMatch': {
                                                                                  '$and': [{'mac': '2'},
                                                                                           {
                                                                                               'manufacturer': '4'
                                                                                  }]}}},
                                                                          {'data._old': {'$ne': True}}]}}},
                                    {'tags': {'$elemMatch': {'$and': [{'plugin_name': 'cisco_prime_adapter'},
                                                                      {'pending_delete': {'$ne': True}},
                                                                      {'data.network_interfaces': {
                                                                          '$elemMatch':
                                                                              {'$and':
                                                                               [{'mac': '2'},
                                                                                {
                                                                                   'manufacturer': '4'
                                                                               }]}}},
                                                                      {'data._old': {'$ne': True}},
                                                                      {'type': 'adapterdata'}]}}}]}]}
                 )


def test_inner_match():
    assert_equal('specific_data == match([plugin_name not in ["esx_adapter"] '
                 'and data.network_interfaces == match([manufacturer == "C"])])',
                 {'$and': [{'$or': [
                     {'adapters': {'$elemMatch': {'$and': [{'$and': [{'plugin_name': {'$nin': ['esx_adapter']}},
                                                                     {'data.network_interfaces': {
                                                                         '$elemMatch': {'manufacturer': 'C'}}}]},
                                                           {'pending_delete': {'$ne': True}},
                                                           {'data._old': {'$ne': True}}]}}},
                     {'tags': {'$elemMatch': {'$and': [{'$and': [{'plugin_name': {'$nin': ['esx_adapter']}},
                                                                 {'data.network_interfaces': {
                                                                     '$elemMatch': {'manufacturer': 'C'}}}]},
                                                       {'pending_delete': {'$ne': True}},
                                                       {'data._old': {'$ne': True}},
                                                       {'type': 'adapterdata'}]}}}]}]})
