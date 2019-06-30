
from scripts.instances.instances_consts import WEAVE_NETWORK_SUBNET_KEY
from upgrade.upgrade_test_utils.customer_conf import read_upgrade_test_customer_data, write_upgrade_test_customer_conf

NEW_WEAVE_NETWORK = '173.17.0.0/16'


def test_change_weave_net():
    conf = read_upgrade_test_customer_data()
    conf[WEAVE_NETWORK_SUBNET_KEY] = NEW_WEAVE_NETWORK
    write_upgrade_test_customer_conf(conf)
