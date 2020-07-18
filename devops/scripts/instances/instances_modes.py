from enum import Enum

from conf_tools import get_customer_conf_json
from scripts.instances.instances_consts import INSTANCE_MODE


class InstancesModes(Enum):
    mongo_only = 'mongo_only'
    remote_mongo = 'remote_mongo'

    @classmethod
    def has_value(cls, value):
        # pylint: disable=no-member
        return value in cls._value2member_map_


def get_instance_mode():
    """
    Get instance mode from customer conf
    :return: instance mode
    """
    conf = get_customer_conf_json()
    instance_mode = conf.get(INSTANCE_MODE)
    if not instance_mode:
        return
    if InstancesModes.has_value(instance_mode):
        return instance_mode
    raise ValueError('Bad instance mode')
