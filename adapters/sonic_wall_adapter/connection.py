import logging
from collections import defaultdict

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from sonic_wall_adapter.consts import API_PREFIX, ADDRESS_OBJECTS, INTERFACES_IPV4_API_PREFIX, ACCESS_RULES, \
    INTERFACES_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class SonicWallConnection(RESTConnection):
    """ rest client for SonicWall adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._post('auth', do_basic_auth=True)
            self._get(INTERFACES_IPV4_API_PREFIX)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _logout(self):
        try:
            self._delete('auth')
        except Exception as e:
            message = f'Logout failed! - {str(e)}'
            logger.warning(message, exc_info=RESTException(message))
        else:
            logger.info(f'Successfully logged out from {self._domain} with {self._username}')
        finally:
            self._session_headers.clear()

    def close(self):
        self._logout()
        super().close()

    def _get_objects_access_rules(self):
        try:
            objects_access_rules = defaultdict(list)

            for access_rule_address, access_rule_type in ACCESS_RULES:
                response = self._get(access_rule_address)
                if not (isinstance(response, dict) and
                        isinstance(response.get('access_rules'), list)):
                    logger.warning(f'Received invalid response for {access_rule_type} access rule. {response}')
                    return {}

                for access_rule in response.get('access_rules') or []:
                    if isinstance(access_rule, dict) and isinstance(access_rule.get(access_rule_type), dict):
                        from_zone = access_rule.get(access_rule_type).get('from')
                        if from_zone is not None:
                            key = (from_zone, access_rule_type)
                            objects_access_rules[key].append(access_rule.get(access_rule_type))

            return objects_access_rules
        except Exception as e:
            logger.warning(f'Failed fetching objects access rules, {str(e)}')
            return {}

    # pylint: disable=too-many-nested-blocks
    def _devices_get(self):
        try:
            objects_access_rules = self._get_objects_access_rules()

            for address, addr_obj_type in ADDRESS_OBJECTS:
                try:
                    response = self._get(address)
                    if not (isinstance(response, dict) and
                            isinstance(response.get('address_objects'), list)):
                        logger.warning(f'Received invalid response for {addr_obj_type} devices. {response}')
                        continue

                    for address_object in response.get('address_objects') or []:
                        if isinstance(address_object, dict) and isinstance(address_object.get(addr_obj_type), dict):
                            device = address_object.get(addr_obj_type)
                            if device and device.get('zone'):
                                key = (device.get('zone'), addr_obj_type)
                                device['access_rules'] = objects_access_rules.get(key) or []

                            yield device, addr_obj_type
                except Exception as e:
                    logger.exception(f'Invalid request made while paginating {addr_obj_type} devices')
                    raise

        except Exception:
            logger.exception(f'Failed getting devices')
            raise

    def _interfaces_get(self):
        try:
            response = self._get(INTERFACES_IPV4_API_PREFIX)
            if not (isinstance(response, dict) and
                    isinstance(response.get('interfaces'), list)):
                logger.warning(f'Received invalid response for interface devices. {response}')
                return

            for interface in response.get('interfaces') or []:
                if isinstance(interface, dict) and isinstance(interface.get('ipv4'), dict):
                    yield interface.get('ipv4'), INTERFACES_TYPE

        except Exception:
            logger.exception(f'Invalid request made while paginating interface devices')
            raise

    def get_device_list(self):
        try:
            yield from self._devices_get()
            yield from self._interfaces_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
