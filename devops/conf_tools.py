import json

from axonius.consts.system_consts import CUSTOMER_CONF_PATH
from scripts.instances.instances_consts import AXONIUS_SETTINGS_HOST_PATH


def get_customer_conf_json():
    try:
        if not CUSTOMER_CONF_PATH.is_file():
            return {}
        return json.loads(CUSTOMER_CONF_PATH.read_text())
    except FileNotFoundError:
        return dict()


def store_as_customer_conf(conf: dict):
    as_json = json.dumps(conf)
    AXONIUS_SETTINGS_HOST_PATH.mkdir(exist_ok=True)
    CUSTOMER_CONF_PATH.write_text(as_json)
