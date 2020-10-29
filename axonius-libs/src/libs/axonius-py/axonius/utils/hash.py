import hashlib
import secrets
import logging
from passlib.hash import bcrypt

from axonius.consts.gui_consts import FeatureFlagsNames
from axonius.entities import EntityType
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.utils.build_modes import is_fed_build_mode

logger = logging.getLogger(f'axonius.{__name__}')


def get_preferred_internal_axon_id_from_dict(device_dict: dict, entity_type: EntityType) -> str:
    """
    See get_preferred_internal_axon_id
    Extracts the plugin_unique_name and id from the given device dict and uses the entity type given
    """
    return get_preferred_internal_axon_id(device_dict[PLUGIN_UNIQUE_NAME],
                                          device_dict['data']['id'], entity_type)


def get_preferred_internal_axon_id(plugin_unique_name: str, _id: str, entity_type: EntityType) -> str:
    """
    When saving entities, we want to try to maintain consistency as much as possible.
    https://axonius.atlassian.net/browse/AX-2980
    """
    return hashlib.md5(f'{entity_type.value}!{plugin_unique_name}!{_id}-v2'.encode('utf-8')).hexdigest()


def get_preferred_quick_adapter_id(plugin_unique_name: str, _id: str) -> str:
    """
    Improved lookup performance
    https://axonius.atlassian.net/browse/AX-5214
    """
    # Warning! do not change. If you change, you affect aggregator_service.py which uses this function for migrations.
    # Change appropriately to include a v2 version.
    return f'{plugin_unique_name}!{_id}'


def is_pbkdf2_enable_for_user_account() -> bool:
    """
     return if  of feature flag PBKDF2 enabled
    """
    from axonius.modules.common import AxoniusCommon
    try:
        return AxoniusCommon().feature_flags().get(FeatureFlagsNames.EnablePBKDF2FedOnly, False)
    except Exception:
        logger.error(f'{FeatureFlagsNames.EnablePBKDF2FedOnly} was not found ! ')
    return False


def user_password_to_pbkdf2_hmac(password, salt) -> hex:
    return hashlib.pbkdf2_hmac('sha512', bytes(password.encode('utf-8')), bytearray.fromhex(salt), 100000).hex()


def user_password_handler(password) -> tuple:
    """
    hash local user password
    for FED BUILDS use pbkdf2 other bcrypt
    :param password: raw password to hash
    :return:
    """
    if is_fed_build_mode() and is_pbkdf2_enable_for_user_account():
        salt = secrets.token_hex(16)
        return user_password_to_pbkdf2_hmac(password, salt), salt
    return bcrypt.hash(password), None


def verify_user_password(password, hash_password, salt=None) -> bool:
    """
    compare user saved hash password with clear text password
     for FED BUILDS use pbkdf2 other bcrypt

    :param password: clear text password
    :param hash_password: db saved user hash
    :param salt:  db saved user uniq salt
    :return:
    """
    if is_fed_build_mode() and is_pbkdf2_enable_for_user_account():
        if salt:
            return user_password_to_pbkdf2_hmac(password, salt) == hash_password
        raise ValueError('User salt is missing')
    return bcrypt.verify(password, hash_password)
