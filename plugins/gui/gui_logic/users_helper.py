from axonius.consts.gui_consts import UNCHANGED_MAGIC_FOR_GUI
from gui.gui_logic.db_helpers import beautify_db_entry


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
                                                   'permissions',
                                                   'role_name',
                                                   'admin',
                                                   'source',
                                                   'additional_userinfo']}
    user['password'] = UNCHANGED_MAGIC_FOR_GUI
    return user
