"""
Test Translation and Projection
"""
import unittest
import datetime
from axonius.entities import EntityType
import axonius.pql.matching
from gui.logic.graphql.translator import Translator
from ui_tests.tests.ui_consts import DEVICES_SEEN_IN_LAST_7_DAYS_QUERY

# hack parse date so it will return a constant date
axonius.pql.matching.parse_date = lambda x: datetime.datetime(year=2020, month=6, day=6)


def get_timestamp():
    return datetime.datetime(year=2020, month=6, day=6).timestamp() * 1000


SAVED_QUERIES = [

    ('Ad devices missing agents', '((adapters_data.active_directory_adapter.id == ({"$exists":true,"$ne":""}))) '
     'and (specific_data.data.last_seen >= date("NOW - 30d")) '
     'and not (specific_data.data.adapter_properties == "Agent")',
     {'AND': [{'adapterDevices': {'adapterName': {'eq': 'active_directory_adapter'}}},
              {'adapterDevices': {'lastSeen': {'gte': get_timestamp()}}},
              {'adapterDevices': {'adapter': {'properties': {'no_overlap': [{'$not': 'Agent'}]}}}}]}),

    ('Devices manufactured in US',
     '((specific_data.data.network_interfaces.manufacturer == ({"$exists":true,"$ne":""}))) '
     'and not (specific_data.data.network_interfaces.manufacturer == regex("US", "i"))',
     {'AND': [{'adapterDevices': {'interfaces': {'manufacturer': {'exists': True}}}},
              {'adapterDevices': {'interfaces': {'manufacturer': {'not_ilike': '%US%'}}}}]}),

    ('Devices Last seen in 7 days', 'specific_data.data.last_seen >= date("NOW - 7d")',
     {'adapterDevices': {'lastSeen': {'gte': get_timestamp()}}}),

    ('Devices not seen last 30 days', 'not (specific_data.data.last_seen >= date("NOW - 30d"))',
     {'adapterDevices': {'lastSeen': {'lt': get_timestamp()}}}),
]

USER_QUERIES = [
    ('Disabled Admins',
     '(specific_data.data.is_admin == true) and (specific_data.data.account_disabled == false)',
     {'AND': [{'adapterUsers': {'admin': {'eq': True}}}, {'adapterUsers': {'disabled': {'eq': False}}}]}
     ),
    (
        'User created last 30 days',
        '(specific_data.data.user_created >= date("NOW - 30d"))',
        {'adapterUsers': {'creationDate': {'gte': get_timestamp()}}}
    ),
    (
        'User last bad logon 7 days',
        '(specific_data.data.last_bad_logon >= date("NOW - 7d"))',
        {'adapterUsers': {'lastBadLogon': {'gte': get_timestamp()}}}
    ),
    (
        'non-local users',
        '(specific_data.data.is_local == false)',
        {'adapterUsers': {'local': {'eq': False}}}
    ),
    (
        'Active admin users with passwords not changed in the last 30 days',
        '(specific_data.data.is_admin == true) and ((specific_data.data.last_password_change == ({"$exists":true,'
        '"$ne":null}))) and not (specific_data.data.last_password_change >= date("NOW - 30d")) and ('
        'specific_data.data.account_disabled == false) and (specific_data.data.last_seen >= date("NOW - 7d"))',
        {'AND': [{'adapterUsers': {'admin': {'eq': True}}},
                 {'adapterUsers': {'lastPasswordChange': {'exists': True}}},
                 {'adapterUsers': {'lastPasswordChange': {'lt': get_timestamp()}}},
                 {'adapterUsers': {'disabled': {'eq': False}}},
                 {'adapterUsers': {'lastSeen': {'gte': get_timestamp()}}}]},
    ),
    (
        # Password required in Postgres is saved as a positive not negative.
        'Password Required',
        '(specific_data.data.password_not_required == true)',
        {'adapterUsers': {'passwordRequired': {'eq': False}}},
    ),
    (
        'At least 3 adapters',
        '(adapter_list_length > 3)',
        {'adapterCount': {'gt': 3}},
    )


    # (
    #     '',
    #     '(specific_data.data.account_disabled == false) '
    #     'and not (specific_data.data.last_password_change >= date("NOW - 30d")) '
    #     'and (specific_data.data.last_seen >= date("NOW - 7d")) '
    #     'and (((specific_data.data.first_name == ({"$exists":true,"$ne":""}))) '
    #     'or ((specific_data.data.image == ({"$exists":true,"$ne":""}))))'
    # )

]


class TestTranslator(unittest.TestCase):

    SIMPLE_ADAPTER_PROPERTIES = '(specific_data.data.adapter_properties == "Vulnerability_Assessment")'
    SIZE_QUERY_INTERFACES = '(specific_data.data.network_interfaces.ips == size(1))'
    REGEX_QUERY_W_OR = '(specific_data.data.hostname == regex("66", "i")) or (specific_data.data.hostname == "ttt")'
    ADAPTER_PROP_W_OR = '(specific_data.data.adapter_properties == "Agent")' \
                        'or (specific_data.data.adapter_properties == "Manager")'
    ADAPTER_EXISTS = '((adapters_data.active_directory_adapter.id == ({"$exists":true,"$ne":""})))'

    TEST_LOGICAL_NOT = '((adapters_data.active_directory_adapter.id == ({"$exists":true,"$ne":""}))) ' \
                       'and not (specific_data.data.name == "test")'
    COMPLEX_DAY_NOT_ADAPTER = '((adapters_data.active_directory_adapter.id == ({"$exists":true,"$ne":""}))) ' \
                              'and (specific_data.data.last_seen >= date("NOW - 30d")) ' \
                              'and not (specific_data.data.adapter_properties == "Agent")'
    NI_MANUFACTURER = '(specific_data.data.network_interfaces.manufacturer == regex("us", "i"))'

    OS_COMMON_FIELD = '(specific_data.data.os.distribution == regex("554", "i"))'
    IFACE_VLANS = '(specific_data.data.network_interfaces.vlan_list.name == regex("554", "i"))'

    def test_device_simple_queries(self):
        """
        Test simple queries, mostly looking at conversions and special methods
        """

        w = Translator(EntityType.Devices).translate(self.SIMPLE_ADAPTER_PROPERTIES)
        self.assertEqual({'adapterDevices': {'adapter': {'properties': {'overlap': ['Vulnerability_Assessment']}}}}, w)
        w = Translator(EntityType.Devices).translate(self.SIZE_QUERY_INTERFACES)
        self.assertEqual({'adapterDevices': {'interfaces': {'ipAddrs': {'size': 1}}}}, w)
        w = Translator(EntityType.Devices).translate(DEVICES_SEEN_IN_LAST_7_DAYS_QUERY)

        # Note: that we can use the Days operator but since AQL converts it already into a datetime, we use GTE
        self.assertEqual({'adapterDevices': {'lastSeen': {'gte': get_timestamp()}}}, w)
        w = Translator(EntityType.Devices).translate(self.ADAPTER_EXISTS)
        self.assertEqual({'adapterDevices': {'adapterName': {'eq': 'active_directory_adapter'}}}, w)

        w = Translator(EntityType.Devices).translate(self.NI_MANUFACTURER)
        self.assertEqual({'adapterDevices': {'interfaces': {'manufacturer': {'ilike': '%us%'}}}}, w)

        w = Translator(EntityType.Devices).translate(self.OS_COMMON_FIELD)
        self.assertEqual({'adapterDevices': {'os': {'distribution': {'ilike': '%554%'}}}}, w)

        w = Translator(EntityType.Devices).translate(self.IFACE_VLANS)
        self.assertEqual({'adapterDevices': {'interfaces': {'vlans': {'name': {'ilike': '%554%'}}}}}, w)

    def test_logical_queries(self):
        """
        Test logical queries of AND, OR and NOT
        """
        w = Translator(EntityType.Devices).translate(self.REGEX_QUERY_W_OR)
        self.assertEqual({'OR': [
            {'hostnames': {'contains_regex': '%66%'}},
            {'adapterDevices': {'hostname': {'eq': 'ttt'}}}]}, w)
        w = Translator(EntityType.Devices).translate(self.ADAPTER_PROP_W_OR)
        self.assertEqual({'OR': [
            {'adapterDevices': {'adapter': {'properties': {'overlap': ['Agent']}}}},
            {'adapterDevices': {'adapter': {'properties': {'overlap': ['Manager']}}}}
        ]}, w)

        w = Translator(EntityType.Devices).translate(self.TEST_LOGICAL_NOT)
        self.assertEqual({'AND': [
            {'adapterDevices': {'adapterName': {'eq': 'active_directory_adapter'}}},
            {'adapterDevices': {'name': {'eq': 'test'}}}]}, w)

        w = Translator(EntityType.Devices).translate(self.COMPLEX_DAY_NOT_ADAPTER)
        self.assertEqual({'AND': [
            {'adapterDevices': {'adapterName': {'eq': 'active_directory_adapter'}}},
            {'adapterDevices': {'lastSeen': {'gte': get_timestamp()}}},
            {'adapterDevices': {'adapter': {'properties': {'no_overlap': [{'$not': 'Agent'}]}}}}]}, w)

    def test_device_save_queries(self):
        for name, aql, expected_gql in SAVED_QUERIES:
            gql = Translator(EntityType.Devices).translate(aql)
            self.assertEqual(expected_gql, gql, name)

    def test_user_queries(self):
        for name, aql, expected_gql in USER_QUERIES:
            gql = Translator(EntityType.Users).translate(aql)
            self.assertEqual(expected_gql, gql, name)


if __name__ == '__main__':
    unittest.main()
