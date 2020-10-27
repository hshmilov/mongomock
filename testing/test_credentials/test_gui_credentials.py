import bcrypt

from axonius.consts.plugin_consts import AXONIUS_USER_NAME, AXONIUS_RO_USER_NAME

DEFAULT_USER = {'user_name': 'admin', 'password': 'cAll2SecureAll'}
AXONIUS_USER = {'user_name': AXONIUS_USER_NAME, 'password': 'wgisBEbF3OdY1Vm60A6Q'}
AXONIUS_RO_USER = {'user_name': AXONIUS_RO_USER_NAME, 'password': 'a04e1e6ef478616dc23f2b62'}
AXONIUS_AWS_TESTS_USER = {'user_name': 'admin2', 'password': 'kjhsjdhbfnlkih43598sdfnsdfjkh'}


def axonius_set_test_passwords():
    from services.axonius_service import get_service

    axonius_system = get_service()
    users = [AXONIUS_USER, AXONIUS_RO_USER, DEFAULT_USER]
    for u in users:
        _set_password(axonius_system, u['user_name'], u['password'])


def _set_password(axonius_system, username, password):
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    axonius_system.db.gui_users_collection().update_one(
        {'user_name':  username},
        {'$set': {'password': hashed_password}}
    )
