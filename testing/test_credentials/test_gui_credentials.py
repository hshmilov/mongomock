import secrets
import bcrypt

from axonius.consts.gui_consts import FeatureFlagsNames, FEATURE_FLAGS_CONFIG
from axonius.consts.plugin_consts import AXONIUS_USER_NAME, AXONIUS_RO_USER_NAME
from axonius.utils.hash import user_password_to_pbkdf2_hmac

DEFAULT_USER = {'user_name': 'admin', 'password': 'cAll2SecureAll'}
AXONIUS_USER = {'user_name': AXONIUS_USER_NAME, 'password': 'wgisBEbF3OdY1Vm60A6Q'}
AXONIUS_RO_USER = {'user_name': AXONIUS_RO_USER_NAME, 'password': 'a04e1e6ef478616dc23f2b62'}
AXONIUS_AWS_TESTS_USER = {'user_name': 'admin2', 'password': 'kjhsjdhbfnlkih43598sdfnsdfjkh'}

'''
User password schema:
---------------------
Regular Build -> bcrypt
Federal Build -> pbkdf2
'''


def axonius_set_test_passwords():
    from services.axonius_service import get_service

    axonius_system = get_service()
    users = [AXONIUS_USER, AXONIUS_RO_USER, DEFAULT_USER]
    for u in users:
        _set_password(axonius_system, u['user_name'], u['password'])


def _set_password(axonius_system, username, password):
    def _update_user_password(hashed_password, user_salt=None):
        axonius_system.db.gui_users_collection().update_one(
            {'user_name': username},
            {'$set': {'password': hashed_password, 'salt': user_salt}}
        )

    if axonius_system.db.plugins.gui.configurable_configs[FEATURE_FLAGS_CONFIG][FeatureFlagsNames.EnablePBKDF2FedOnly]:
        salt = secrets.token_hex(16)
        _update_user_password(user_password_to_pbkdf2_hmac(password, salt), salt)
    else:
        _update_user_password(bcrypt.hashpw(password.encode(), bcrypt.gensalt()))
