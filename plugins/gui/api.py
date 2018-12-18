import logging
import math

from passlib.hash import bcrypt
from flask import jsonify, request
from typing import Iterable

from axonius.plugin_base import EntityType, return_error
from axonius.utils import gui_helpers
from axonius.utils.gui_helpers import Permission, check_permissions, deserialize_db_permissions, PermissionType, \
    PermissionLevel, ReadOnlyJustForGet

logger = logging.getLogger(f'axonius.{__name__}')

API_VERSION = "1"


# Caution! These decorators must come BEFORE @add_rule
def basic_authentication(func, required_permissions: Iterable[Permission]):
    """
    Decorator stating that the view requires the user to be connected
    """

    def wrapper(self, *args, **kwargs):
        users_collection = self._get_collection("users")

        def check_auth_user(username, password):
            """
            This function is called to check if a username /
            password combination is valid.
            """
            user_from_db = users_collection.find_one({"user_name": username})
            if user_from_db is None:
                logger.info(f"Unknown user {username} tried logging in")
                return False
            if not bcrypt.verify(password, user_from_db["password"]):
                return False
            if user_from_db.get('admin'):
                return True
            if not check_permissions(deserialize_db_permissions(user_from_db['permissions']),
                                     required_permissions,
                                     request.method):
                return False
            return True

        def check_auth_api_key(api_key, api_secret):
            """
            This function is called to check if an api key and secret match
            """
            user_from_db = users_collection.find_one({
                'api_key': api_key,
                'api_secret': api_secret
            })

            if not user_from_db:
                return False
            if user_from_db.get('admin'):
                return True
            if not check_permissions(deserialize_db_permissions(user_from_db['permissions']),
                                     required_permissions,
                                     request.method):
                return False
            return True

        api_auth = request.headers.get('api-key'), request.headers.get('api-secret')
        auth = request.authorization
        if check_auth_api_key(*api_auth) or (auth and check_auth_user(auth.username, auth.password)):
            return func(self, *args, **kwargs)

        return return_error("Unauthorized", 401)

    return wrapper


def api_add_rule(rule, required_permissions: Iterable[Permission] = None, *args, **kwargs):
    """
    A URL mapping for API endpoints that use the API method to log in (either user and pass or API key)
    """

    def basic_authentication_permissions(*args, **kwargs):
        return basic_authentication(*args, **kwargs, required_permissions=required_permissions)

    return gui_helpers.add_rule_custom_authentication(f"V{API_VERSION}/{rule}", basic_authentication_permissions, *args,
                                                      **kwargs)


def get_page_metadata(skip, limit, number_of_assets):
    logger.info(f"skip this:{skip}")
    logger.info(f"limit this:{limit}")
    return {
        "number": math.floor((skip / limit) + 1) if limit != 0 else 0,  # Current page number
        "size": min(max(number_of_assets - skip, 0), limit),  # Number of assets in current page
        "totalPages": math.ceil(number_of_assets / limit) if limit != 0 else 0,  # Total number of pages
        "totalResources": number_of_assets  # Total number of assets filtered
    }


class API:

    ###########
    # DEVICES #
    ###########
    @gui_helpers.add_rule_unauth(f"api")
    def api_description(self):
        return API_VERSION

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @api_add_rule(f"devices", required_permissions={Permission(PermissionType.Devices,
                                                               PermissionLevel.ReadOnly)})
    def api_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        devices_collection = self._entity_views_db_map[EntityType.Devices]
        self._save_query_to_history(EntityType.Devices, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        return_doc = {
            "page": get_page_metadata(skip, limit,
                                      int(gui_helpers.get_entities_count(mongo_filter, devices_collection))),
            "assets": list(
                gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort,
                                         mongo_projection,
                                         EntityType.Devices,
                                         default_sort=self._system_settings['defaultSort']))
        }

        return jsonify(return_doc)

    @gui_helpers.filtered()
    @api_add_rule(f"devices/count", required_permissions={Permission(PermissionType.Devices,
                                                                     PermissionLevel.ReadOnly)})
    def api_devices_count(self, mongo_filter):
        return gui_helpers.get_entities_count(mongo_filter, self._entity_views_db_map[EntityType.Devices])

    @api_add_rule(f"devices/<device_id>", required_permissions={Permission(PermissionType.Devices,
                                                                           PermissionLevel.ReadOnly)})
    def api_device_by_id(self, device_id):
        return self._device_entity_by_id(device_id)

    @gui_helpers.filtered()
    @api_add_rule("devices/labels", methods=['GET', 'POST', 'DELETE'],
                  required_permissions={Permission(PermissionType.Devices,
                                                   ReadOnlyJustForGet)})
    def api_device_labels(self, mongo_filter):
        return self._entity_labels(self.devices_db_view, self.devices, mongo_filter)

    #########
    # USERS #
    #########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @api_add_rule(f"users", required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadOnly)})
    def api_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        users_collection = self._entity_views_db_map[EntityType.Users]
        self._save_query_to_history(EntityType.Users, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        return_doc = {
            "page": get_page_metadata(skip, limit, int(gui_helpers.get_entities_count(mongo_filter, users_collection))),
            "assets": list(
                gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort,
                                         mongo_projection,
                                         EntityType.Users,
                                         default_sort=self._system_settings['defaultSort']))
        }

        return jsonify(return_doc)

    @gui_helpers.filtered()
    @api_add_rule(f"users/count", required_permissions={Permission(PermissionType.Users,
                                                                   PermissionLevel.ReadOnly)})
    def api_users_count(self, mongo_filter):
        return gui_helpers.get_entities_count(mongo_filter, self._entity_views_db_map[EntityType.Users])

    @api_add_rule(f"users/<user_id>", required_permissions={Permission(PermissionType.Users,
                                                                       PermissionLevel.ReadOnly)})
    def api_user_by_id(self, user_id):
        return self._user_entity_by_id(user_id)

    @gui_helpers.filtered()
    @api_add_rule("users/labels", methods=['GET', 'POST', 'DELETE'],
                  required_permissions={Permission(PermissionType.Users,
                                                   ReadOnlyJustForGet)})
    def api_user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db_view, self.users, mongo_filter)

    ##########
    # ALERTS #
    ##########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @api_add_rule(f"alerts", methods=["GET", "PUT", "DELETE"], required_permissions={Permission(PermissionType.Alerts,
                                                                                                ReadOnlyJustForGet)})
    def api_alerts(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        if request.method == "GET":
            alerts = self.get_alerts(limit, mongo_filter, mongo_projection, mongo_sort, skip)
            return_doc = {
                "page": get_page_metadata(skip, limit, len(alerts)),
                "assets": alerts
            }
            return jsonify(return_doc)

        if request.method == "PUT":
            report_to_add = request.get_json(silent=True)
            return self.put_alert(report_to_add)

        if request.method == "DELETE":
            report_ids = self.get_request_data_as_object()
            alert_selection = {
                'ids': report_ids,
                'include': True
            }
            return self.delete_alert(alert_selection)

    ###########
    # QUERIES #
    ###########
    def query_views(self, limit, skip, mongo_filter, entity_type):
        # Assuming only flask endpoints call this function.
        views = self._entity_views(request.method, entity_type, limit, skip, mongo_filter)

        if request.method == "GET":

            return_doc = {
                "page": get_page_metadata(skip, limit, len(views)),
                "assets": views
            }
        else:
            return_doc = views

        return jsonify(return_doc)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @api_add_rule(f"devices/views", methods=["GET", "POST", "DELETE"],
                  required_permissions={Permission(PermissionType.Devices,
                                                   ReadOnlyJustForGet)})
    def api_device_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self.query_views(limit, skip, mongo_filter, EntityType.Devices)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @api_add_rule(f"users/views", methods=["GET", "POST", "DELETE"],
                  required_permissions={Permission(PermissionType.Users,
                                                   ReadOnlyJustForGet)})
    def api_users_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the users db
        :return:
        """
        return self.query_views(limit, skip, mongo_filter, EntityType.Users)

    ###########
    # ACTIONS #
    ###########

    @gui_helpers.filtered()
    @api_add_rule(f"actions/<action_type>", methods=["POST"],
                  required_permissions={Permission(PermissionType.Devices,
                                                   PermissionLevel.ReadWrite)})
    def api_run_actions(self, action_type, mongo_filter):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """

        if action_type == "upload_file":
            return self._upload_file(self.device_control_plugin)

        action_data = self.get_request_data_as_object()
        action_data["action_type"] = action_type
        action_data["entities"] = {
            "ids": action_data["internal_axon_ids"],
            "include": True,
        }
        return self.run_actions(action_data, mongo_filter)

    @api_add_rule(f"actions")
    def api_get_actions(self):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """
        actions = ["deploy", "shell", "upload_file"]
        return jsonify(actions)
