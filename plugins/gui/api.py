import logging
import math

from flask import jsonify, request
from passlib.hash import bcrypt

from axonius.plugin_base import EntityType, return_error
from axonius.utils import gui_helpers

logger = logging.getLogger(f'axonius.{__name__}')

API_VERSION = "1"


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
            users_collection = self._get_collection("users")
            user_from_db = users_collection.find_one({"user_name": username})
            if user_from_db is None:
                logger.info(f"Unknown user {username} tried logging in")
                return False
            return bcrypt.verify(password, user_from_db["password"])

        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return return_error("Unauthorized", 401)
        return func(self, *args, **kwargs)

    return wrapper


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
    @gui_helpers.add_rule_unauthenticated(f"api", methods=["GET"],
                                          auth_method=None)
    def api_description(self):
        return API_VERSION

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/devices", methods=["GET"], auth_method=basic_authentication)
    def api_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return_doc = {
            "page": get_page_metadata(skip, limit, int(self._get_entities_count(mongo_filter, EntityType.Devices))),
            "assets": list(gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                                    self.gui_dbs.entity_query_views_db_map[EntityType.Devices],
                                                    self._entity_views_db_map[EntityType.Devices], EntityType.Devices, True,
                                                    default_sort=self._system_settings["defaultSort"]))
        }

        return jsonify(return_doc)

    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/devices/<device_id>", methods=["GET"],
                                          auth_method=basic_authentication)
    def api_device_by_id(self, device_id):
        return self._entity_by_id(EntityType.Devices, device_id, ["installed_software", "security_patches",
                                                                  "available_security_patches", "users",
                                                                  "connected_hardware", "local_admins"])

    #########
    # USERS #
    #########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/users", auth_method=basic_authentication)
    def api_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return_doc = {
            "page": get_page_metadata(skip, limit, int(self._get_entities_count(mongo_filter, EntityType.Users))),
            "assets": list(gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                                    self.gui_dbs.entity_query_views_db_map[EntityType.Users],
                                                    self._entity_views_db_map[EntityType.Users], EntityType.Users, True,
                                                    default_sort=self._system_settings["defaultSort"]))
        }

        return jsonify(return_doc)

    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/users/<user_id>", methods=["GET"],
                                          auth_method=basic_authentication)
    def api_user_by_id(self, user_id):
        return self._entity_by_id(EntityType.Users, user_id, ["associated_devices"])

    ##########
    # ALERTS #
    ##########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/alerts", methods=["GET", "PUT", "DELETE"],
                                          auth_method=basic_authentication)
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

        report_ids = self.get_request_data_as_object()
        return self.delete_alert(report_ids)

    ###########
    # QUERIES #
    ###########
    def query_views(self, limit, skip, mongo_filter, entity_type):
        # Assuming only flask endpoints call this function.
        views = self._entity_views(request.method, entity_type, limit, skip, mongo_filter)

        if request.method == "GET":

            return_doc = {
                "page": self.calc_page(skip, limit, views),
                "assets": views
            }
        else:
            return_doc = views

        return jsonify(return_doc)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/devices/views", methods=["GET", "POST", "DELETE"],
                                          auth_method=basic_authentication)
    def api_device_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self.query_views(limit, skip, mongo_filter, EntityType.Devices)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/users/views", methods=["GET", "POST", "DELETE"],
                                          auth_method=basic_authentication)
    def api_users_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the users db
        :return:
        """
        return self.query_views(limit, skip, mongo_filter, EntityType.Users)

    ###########
    # ACTIONS #
    ###########

    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/actions/<action_type>", methods=["POST"],
                                          auth_method=basic_authentication)
    def api_run_actions(self, action_type):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """
        action_data = self.get_request_data_as_object()
        action_data["action_type"] = action_type
        return self.run_actions(action_type)

    @gui_helpers.add_rule_unauthenticated(f"V{API_VERSION}/actions", methods=["GET"], auth_method=basic_authentication)
    def api_get_actions(self):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """
        actions = ["deploy", "shell"]
        return jsonify(actions)
