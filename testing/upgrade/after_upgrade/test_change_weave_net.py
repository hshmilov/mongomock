from axonius.utils.network.docker_network import read_weave_network_range
from scripts.instances.instances_consts import WEAVE_NETWORK_SUBNET_KEY
from upgrade.before_upgrade.test_change_weave_net import NEW_WEAVE_NETWORK
from upgrade.upgrade_test_utils.customer_conf import read_upgrade_test_customer_data


def test_change_weave_net():
    conf = read_upgrade_test_customer_data()
    assert conf[WEAVE_NETWORK_SUBNET_KEY] == NEW_WEAVE_NETWORK
    assert conf[WEAVE_NETWORK_SUBNET_KEY] == read_weave_network_range()
