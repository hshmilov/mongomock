import json

from upgrade.upgrade_test_utils.consts import CUSTOMER_CONF_PATH_UPGRADE_TESTS


def write_upgrade_test_customer_conf(data):
    path = CUSTOMER_CONF_PATH_UPGRADE_TESTS
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(data))


def read_upgrade_test_customer_data():
    if CUSTOMER_CONF_PATH_UPGRADE_TESTS.is_file():
        return json.loads(CUSTOMER_CONF_PATH_UPGRADE_TESTS.read_text())
    return {}
