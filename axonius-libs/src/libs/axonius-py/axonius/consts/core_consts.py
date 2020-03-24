from enum import Enum


CORE_CONFIG_NAME = 'CoreService'
ACTIVATED_NODE_STATUS = 'Activated'
DEACTIVATED_NODE_STATUS = 'Deactivated'


class NotificationHookType(Enum):
    """
        This enum represents the different types of hook we can have in a notification.
    """
    LINK = 'link'


LINK_REGEX = r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|' \
             r'www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|' \
             r'(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,}|https?:\/\/(?:www\.|' \
             r'(?!www))(?:localhost)[^\s]{2,})'
