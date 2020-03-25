import logging
from datetime import datetime

from flask import (jsonify,
                   make_response, request)

from axonius.consts.gui_consts import FILE_NAME_TIMESTAMP_FORMAT
from axonius.plugin_base import EntityType
from axonius.utils.db_querying_helper import get_entities
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, ReadOnlyJustForGet, historical,
                                       paginated, filtered_entities, sorted_endpoint,
                                       projected, filtered_fields, entity_fields,
                                       filtered, search_filter, schema_fields as schema)
from axonius.utils.json_encoders import iterator_jsonify
from gui.logic.entity_data import (get_entity_data, entity_data_field_csv,
                                   entity_notes, entity_notes_update, entity_tasks_actions,
                                   entity_tasks_actions_csv)
from gui.logic.generate_csv import get_csv_from_heavy_lifting_plugin
from gui.logic.routing_helper import gui_add_rule_logged_in
from gui.logic.views_data import get_views_count

# pylint: disable=no-member,no-self-use

logger = logging.getLogger(f'axonius.{__name__}')


class Users:
    @historical()
    @paginated()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @gui_add_rule_logged_in('users', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def get_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection, history: datetime):
        if request.method == 'DELETE':
            return self._delete_entities_by_internal_axon_id(
                EntityType.Users, self.get_request_data_as_object(), mongo_filter)
        self._save_query_to_history(EntityType.Users, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        iterable = get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                EntityType.Users,
                                default_sort=self._system_settings['defaultSort'],
                                history_date=history,
                                include_details=True)
        return iterator_jsonify(iterable)

    @historical()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @filtered_fields()
    @gui_add_rule_logged_in('users/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadOnly)})
    def get_users_csv(self, mongo_filter, mongo_sort, mongo_projection, history: datetime, field_filters):
        # Deleting image from the CSV (we dont need this base64 blob in the csv)
        if 'specific_data.data.image' in mongo_projection:
            del mongo_projection['specific_data.data.image']

        return get_csv_from_heavy_lifting_plugin(mongo_filter,
                                                 mongo_sort,
                                                 mongo_projection,
                                                 history,
                                                 EntityType.Users,
                                                 self._system_settings.get('defaultSort'),
                                                 field_filters)

    @historical()
    @filtered_entities()
    @gui_add_rule_logged_in('users/count', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadOnly)})
    def get_users_count(self, mongo_filter, history: datetime):
        content = self.get_request_data_as_object()
        quick = content.get('quick') or request.args.get('quick')
        quick = quick == 'True'
        return self._get_entity_count(EntityType.Users, mongo_filter, history, quick)

    @gui_add_rule_logged_in('users/fields', required_permissions={
        Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def user_fields(self):
        return jsonify(entity_fields(EntityType.Users))

    @filtered_entities()
    @gui_add_rule_logged_in('users/disable', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def disable_user(self, mongo_filter):
        return self._disable_entity(EntityType.Users, mongo_filter)

    @filtered_entities()
    @gui_add_rule_logged_in('users/enforce', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def enforce_user(self, mongo_filter):
        return self._enforce_entity(EntityType.Users, mongo_filter)

    @paginated()
    @filtered()
    @sorted_endpoint()
    @gui_add_rule_logged_in('users/views/<query_type>', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users, ReadOnlyJustForGet)})
    def user_views(self, limit, skip, mongo_filter, mongo_sort, query_type):
        return jsonify(
            self._entity_views(request.method, EntityType.Users, limit, skip, mongo_filter, mongo_sort, query_type))

    @gui_add_rule_logged_in('users/views/saved/<query_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def users_views_update(self, query_id):
        """
        Update name of an existing view
        :return:
        """
        self._entity_views_update(EntityType.Users, query_id)
        return ''

    @gui_add_rule_logged_in('users/views/tags', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def get_users_saved_queries_tags(self):
        return jsonify(self._get_queries_tags_by_entity(EntityType.Users))

    @gui_add_rule_logged_in('users/views/names_list', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def get_users_saved_queries_names_list(self):
        return jsonify(self._get_queries_names_by_entity(EntityType.Users))

    @filtered()
    @gui_add_rule_logged_in('users/views/<query_type>/count', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def get_users_views_count(self, mongo_filter, query_type):
        content = self.get_request_data_as_object()
        quick = content.get('quick') or request.args.get('quick')
        quick = quick == 'True'
        mongo_filter['query_type'] = query_type
        return str(get_views_count(EntityType.Users, mongo_filter, quick=quick))

    @filtered_entities()
    @gui_add_rule_logged_in('users/labels', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db, self.users, mongo_filter)

    @historical()
    @gui_add_rule_logged_in('users/<user_id>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def user_generic(self, user_id, history: datetime):
        res = get_entity_data(EntityType.Users, user_id, history)
        if isinstance(res, dict):
            return jsonify(res)
        return res

    @search_filter()
    @historical()
    @sorted_endpoint()
    @filtered_fields()
    @gui_add_rule_logged_in('users/<user_id>/<field_name>/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def user_generic_field_csv(self, user_id, field_name, mongo_sort, history: datetime, field_filters, search: str):
        """
        Create a csv file for a specific field of a specific entity

        :param user_id:     internal_axon_id of User to create csv for
        :param field_name:  Field of the User, containing table data
        :param mongo_sort:  How to sort the table data of the field
        :param history:     Fetch the User according to this past date
        :param search:      a string to filter the data
        :return:            Response containing csv data, that can be downloaded into a csv file
        """
        csv_string = entity_data_field_csv(EntityType.Users, user_id, field_name,
                                           mongo_sort, history, field_filters, search_term=search)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        field_name = field_name.split('.')[-1]
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{field_name}_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_add_rule_logged_in('users/<user_id>/tasks', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def user_tasks(self, user_id):
        return jsonify(entity_tasks_actions(user_id))

    @schema()
    @sorted_endpoint()
    @gui_add_rule_logged_in('users/<user_id>/tasks/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def user_tasks_csv(self, user_id, mongo_sort, schema_fields):
        """
        Create a csv file for a enforcement tasks of a specific device

        :param user_id:   internal_axon_id of the User tasks to create csv for
        :param mongo_sort:  the sort of the csv
        :param schema_fields:   the fields to show
        :return:            Response containing csv data, that can be downloaded into a csv file
        """
        csv_string = entity_tasks_actions_csv(user_id, schema_fields, mongo_sort)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_enforcement_tasks_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_add_rule_logged_in('users/<user_id>/notes', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def user_notes(self, user_id):
        return entity_notes(EntityType.Users, user_id, self.get_request_data_as_object())

    @gui_add_rule_logged_in('users/<user_id>/notes/<note_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def user_notes_update(self, user_id, note_id):
        return entity_notes_update(EntityType.Users, user_id, note_id, self.get_request_data_as_object()['note'])

    @filtered_entities()
    @gui_add_rule_logged_in('users/custom', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadWrite)})
    def users_custom_data(self, mongo_filter):
        """
        See self._entity_custom_data
        """
        return self._entity_custom_data(EntityType.Users, mongo_filter)

    @gui_add_rule_logged_in('users/hyperlinks', required_permissions={Permission(PermissionType.Users,
                                                                                 PermissionLevel.ReadOnly)})
    def user_hyperlinks(self):
        return jsonify(self._get_entity_hyperlinks(EntityType.Users))

    @filtered_entities()
    @gui_add_rule_logged_in('users/manual_link', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def users_link(self, mongo_filter):
        return self._link_many_entities(EntityType.Users, mongo_filter)

    @filtered_entities()
    @gui_add_rule_logged_in('users/manual_unlink', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadWrite)})
    def users_unlink(self, mongo_filter):
        return self._unlink_axonius_entities(EntityType.Users, mongo_filter)
