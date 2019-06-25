import json

from axonius.consts.system_consts import CUSTOMER_CONF_PATH


def get_customer_conf_json():
    try:
        return json.loads(CUSTOMER_CONF_PATH.read_text())
    except FileNotFoundError:
        return dict()
