import codecs
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


class Devices:
    @historical()
    @paginated()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @gui_add_rule_logged_in('devices', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def get_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection, history: datetime):
        if request.method == 'DELETE':
            return self._delete_entities_by_internal_axon_id(
                EntityType.Devices, self.get_request_data_as_object(), mongo_filter)
        # Filter all _preferred fields because they're calculated dynamically, instead filter by original values
        mongo_sort = {x.replace('_preferred', ''): mongo_sort[x] for x in mongo_sort}
        self._save_query_to_history(EntityType.Devices, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        iterable = get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                EntityType.Devices,
                                default_sort=self._system_settings.get('defaultSort'),
                                history_date=history,
                                include_details=True)
        return iterator_jsonify(iterable)

    @historical()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @filtered_fields()
    @gui_add_rule_logged_in('devices/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def get_devices_csv(self, mongo_filter, mongo_sort, mongo_projection, history: datetime, field_filters):
        return get_csv_from_heavy_lifting_plugin(mongo_filter,
                                                 mongo_sort,
                                                 mongo_projection,
                                                 history,
                                                 EntityType.Devices,
                                                 self._system_settings.get('defaultSort'),
                                                 field_filters)

    @filtered_entities()
    @historical()
    @gui_add_rule_logged_in('devices/count', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def get_devices_count(self, mongo_filter, history: datetime):
        content = self.get_request_data_as_object()
        quick = content.get('quick') or request.args.get('quick')
        quick = quick == 'True'
        return str(self._get_entity_count(EntityType.Devices, mongo_filter, history, quick))

    @gui_add_rule_logged_in('devices/fields',
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def device_fields(self):
        return jsonify(entity_fields(EntityType.Devices))

    @paginated()
    @filtered()
    @sorted_endpoint()
    @gui_add_rule_logged_in('devices/views/<query_type>', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, ReadOnlyJustForGet)})
    def device_views(self, limit, skip, mongo_filter, mongo_sort, query_type):
        """
        Save or fetch views over the devices db
        :return:
        """
        return jsonify(
            self._entity_views(request.method, EntityType.Devices, limit, skip, mongo_filter, mongo_sort, query_type))

    @gui_add_rule_logged_in('devices/views/saved/<query_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def device_views_update(self, query_id):
        """
        Update name of an existing view
        :return:
        """
        self._entity_views_update(EntityType.Devices, query_id)
        return ''

    @gui_add_rule_logged_in('devices/views/tags', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def get_devices_saved_queries_tags(self):
        return jsonify(self._get_queries_tags_by_entity(EntityType.Devices))

    @gui_add_rule_logged_in('devices/views/names_list', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def get_devices_saved_queries_names_list(self):
        return jsonify(self._get_queries_names_by_entity(EntityType.Devices))

    @filtered()
    @gui_add_rule_logged_in('devices/views/<query_type>/count', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def get_devices_views_count(self, mongo_filter, query_type):
        content = self.get_request_data_as_object()
        quick = content.get('quick') or request.args.get('quick')
        quick = quick == 'True'
        mongo_filter['query_type'] = query_type
        return str(get_views_count(EntityType.Devices, mongo_filter, quick=quick))

    @filtered_entities()
    @gui_add_rule_logged_in('devices/labels', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, ReadOnlyJustForGet)})
    def device_labels(self, mongo_filter):
        return self._entity_labels(self.devices_db, self.devices, mongo_filter)

    @filtered_entities()
    @gui_add_rule_logged_in('devices/disable', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def disable_device(self, mongo_filter):
        return self._disable_entity(EntityType.Devices, mongo_filter)

    @filtered_entities()
    @gui_add_rule_logged_in('devices/enforce', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def enforce_device(self, mongo_filter):
        return self._enforce_entity(EntityType.Devices, mongo_filter)

    @historical()
    @gui_add_rule_logged_in('devices/<device_id>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_generic(self, device_id, history: datetime):
        res = get_entity_data(EntityType.Devices, device_id, history)
        if isinstance(res, dict):
            return jsonify(res)
        return res

    @search_filter()
    @historical()
    @sorted_endpoint()
    @gui_add_rule_logged_in('devices/<device_id>/<field_name>/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_generic_field_csv(self, device_id, field_name, mongo_sort, history: datetime, search: str):
        """
        Create a csv file for a specific field of a specific device

        :param device_id:   internal_axon_id of the Device to create csv for
        :param field_name:  Field of the Device, containing table data
        :param mongo_sort:  How to sort the table data of the field
        :param history:     Fetch the Device according to this past date
        :param search:      a string to filter the data
        :return:            Response containing csv data, that can be downloaded into a csv file
        """
        csv_string = entity_data_field_csv(EntityType.Devices, device_id, field_name,
                                           mongo_sort, history, search_term=search)
        output = make_response((codecs.BOM_UTF8 * 2) + csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        field_name = field_name.split('.')[-1]
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{field_name}_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_add_rule_logged_in('devices/<device_id>/tasks', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_tasks(self, device_id):
        return jsonify(entity_tasks_actions(device_id))

    @gui_add_rule_logged_in('devices/<device_id>/notes', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def device_notes(self, device_id):
        return entity_notes(EntityType.Devices, device_id, self.get_request_data_as_object())

    @schema()
    @sorted_endpoint()
    @gui_add_rule_logged_in('devices/<device_id>/tasks/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_tasks_csv(self, device_id, mongo_sort, schema_fields):
        """
        Create a csv file for a enforcement tasks of a specific device

        :param device_id:   internal_axon_id of the Device tasks to create csv for
        :param mongo_sort:  the sort of the csv
        :param schema_fields:   the fields to show
        :return:            Response containing csv data, that can be downloaded into a csv file
        """
        csv_string = entity_tasks_actions_csv(device_id, schema_fields, mongo_sort)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_enforcement_tasks_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_add_rule_logged_in('devices/<device_id>/notes/<note_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def device_notes_update(self, device_id, note_id):
        return entity_notes_update(EntityType.Devices, device_id, note_id, self.get_request_data_as_object()['note'])

    @filtered_entities()
    @gui_add_rule_logged_in('devices/custom', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def devices_custom_data(self, mongo_filter):
        """
        See self._entity_custom_data
        """
        return self._entity_custom_data(EntityType.Devices, mongo_filter)

    @gui_add_rule_logged_in('devices/hyperlinks', required_permissions={Permission(PermissionType.Devices,
                                                                                   PermissionLevel.ReadOnly)})
    def device_hyperlinks(self):
        return jsonify(self._get_entity_hyperlinks(EntityType.Devices))

    @filtered_entities()
    @gui_add_rule_logged_in('devices/manual_link', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def devices_link(self, mongo_filter):
        return self._link_many_entities(EntityType.Devices, mongo_filter)

    @filtered_entities()
    @gui_add_rule_logged_in('devices/manual_unlink', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def devices_unlink(self, mongo_filter):
        return self._unlink_axonius_entities(EntityType.Devices, mongo_filter)
