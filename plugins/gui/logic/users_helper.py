from axonius.consts.gui_consts import UNCHANGED_MAGIC_FOR_GUI, PREDEFINED_FIELD, IS_AXONIUS_ROLE
from axonius.utils.permissions_helper import serialize_db_permissions
from gui.logic.db_helpers import beautify_db_entry


def beautify_user_entry(user):
    """
    Takes a user from DB form and converts it to the form the GUI accepts.
    Takes off password field and other sensitive information.
    :param entry:
    :return:
    """
    user = beautify_db_entry(user)
    user = {k: v for k, v in user.items() if k in ['uuid',
                                                   'user_name',
                                                   'first_name',
                                                   'last_name',
                                                   'pic_name',
                                                   'admin',
                                                   'source',
                                                   'timeout',
                                                   'role_id',
                                                   'permissions',
                                                   'role_name',
                                                   'environment_name',
                                                   'email',
                                                   'last_login',
                                                   'last_updated',
                                                   'ignore_role_assignment_rules',
                                                   PREDEFINED_FIELD,
                                                   IS_AXONIUS_ROLE,
                                                   ]}
    user['role_id'] = str(user.get('role_id'))
    if user.get('permissions'):
        user['permissions'] = serialize_db_permissions(user.get('permissions'))
    if user.get('salt'):
        user.pop('salt')
    user['password'] = UNCHANGED_MAGIC_FOR_GUI
    return user
