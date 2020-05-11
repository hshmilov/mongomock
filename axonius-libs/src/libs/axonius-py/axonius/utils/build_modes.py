from enum import Enum
import os

AX_MODE_ENV_NAME = 'AX_MODE'


class BuildModes(Enum):
    fed = 'FED'

    @classmethod
    def has_value(cls, value):
        # pylint: disable=no-member
        return value in cls._value2member_map_


def get_build_mode():
    """
    Get build mode from emv var
    :return: build mode
    """
    mode = os.getenv(AX_MODE_ENV_NAME)
    if mode and BuildModes.has_value(mode):
        return mode
    return None
