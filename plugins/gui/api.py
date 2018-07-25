from flask import jsonify, request
from axonius.utils import gui_helpers
from axonius.plugin_base import EntityType, return_error
import logging
from passlib.hash import bcrypt

logger = logging.getLogger(f"axonius.{__name__}")

api_version = '1'


# Caution! These decorators must come BEFORE @add_rule
def basic_authentication(func):
    """
    Decorator stating that the view requires the user to be connected
    """

    def wrapper(self, *args, **kwargs):
        def check_auth(username, password):
            """This function is called to check if a username /
            password combination is valid.
            """
            users_collection = self._get_collection('users')
            user_from_db = users_collection.find_one({'user_name': username})
            if user_from_db is None:
                logger.info(f"Unknown user {username} tried logging in")
                return False
            return bcrypt.verify(password, user_from_db['password'])

        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return return_error("Unauthorized", 401)
        return func(self, *args, **kwargs)

    return wrapper


class API:

    ###########
    # DEVICES #
    ###########
    @gui_helpers.add_rule_unauthenticated(f'api', methods=['GET'],
                                          auth_method=None)
    def api_description(self):
        return api_version

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/devices', methods=['GET'], auth_method=basic_authentication)
    def api_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return jsonify(
            gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                     self.gui_dbs.entity_query_views_db_map[EntityType.Devices],
                                     self._entity_views_db_map[EntityType.Devices], EntityType.Devices, True,
                                     default_sort=self._system_settings['defaultSort']))

    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/devices/<device_id>', methods=['GET'],
                                          auth_method=basic_authentication)
    def api_device_by_id(self, device_id):
        return self._entity_by_id(EntityType.Devices, device_id, ['installed_software', 'security_patches',
                                                                  'available_security_patches', 'users',
                                                                  'connected_hardware', 'local_admins'])

    #########
    # USERS #
    #########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/users', auth_method=basic_authentication)
    def api_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return jsonify(
            gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                     self.gui_dbs.entity_query_views_db_map[EntityType.Users],
                                     self._entity_views_db_map[EntityType.Users], EntityType.Users, True,
                                     default_sort=self._system_settings['defaultSort']))

    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/users/<user_id>', methods=['GET'],
                                          auth_method=basic_authentication)
    def api_user_by_id(self, user_id):
        return self._entity_by_id(EntityType.Users, user_id, ['associated_devices'])

    ##########
    # ALERTS #
    ##########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/alerts', methods=['GET', 'PUT', 'DELETE'],
                                          auth_method=basic_authentication)
    def api_alerts(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        if request.method == 'GET':
            return jsonify(self.get_alerts(limit, mongo_filter, mongo_projection, mongo_sort, skip))

        if request.method == 'PUT':
            report_to_add = request.get_json(silent=True)
            return self.put_alert(report_to_add)

        report_ids = self.get_request_data_as_object()
        return self.delete_alert(report_ids)

    ###########
    # QUERIES #
    ###########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/devices/views', methods=['GET', 'POST', 'DELETE'],
                                          auth_method=basic_authentication)
    def api_device_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self._entity_views(request.method, EntityType.Devices, limit, skip, mongo_filter)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/users/views', methods=['GET', 'POST', 'DELETE'],
                                          auth_method=basic_authentication)
    def api_device_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self._entity_views(request.method, EntityType.Users, limit, skip, mongo_filter)

        ###########
        # QUERIES #
        ###########

    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/actions/<action_type>', methods=['POST'], auth_method=basic_authentication)
    def api_run_actions(self, action_type):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """
        action_data = self.get_request_data_as_object()
        action_data['action_type'] = action_type
        return self.run_actions(action_type)

    @gui_helpers.add_rule_unauthenticated(f'V{api_version}/actions', methods=['GET'], auth_method=basic_authentication)
    def api_get_actions(self):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """
        actions = ['deploy', 'shell']
        return jsonify(actions)
