import codecs
import logging
import re
from datetime import datetime

from flask import (jsonify,
                   make_response, request)

from axonius.consts.gui_consts import FILE_NAME_TIMESTAMP_FORMAT
from axonius.plugin_base import EntityType
from axonius.utils.db_querying_helper import get_entities
from axonius.utils.gui_helpers import (historical, paginated,
                                       filtered_entities, sorted_endpoint,
                                       projected, filtered_fields,
                                       entity_fields, search_filter,
                                       schema_fields as schema)
from axonius.utils.json_encoders import iterator_jsonify
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from gui.logic.entity_data import (get_entity_data, entity_data_field_csv,
                                   entity_notes, entity_notes_update, entity_tasks_actions,
                                   entity_tasks_actions_csv)
from gui.logic.generate_csv import get_csv_from_heavy_lifting_plugin
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.routes.entities.views.views_generator import views_generator

# pylint: disable=no-member,no-self-use

logger = logging.getLogger(f'axonius.{__name__}')


def entity_generator(rule: str, permission_category: PermissionCategory):

    @gui_category_add_rules(rule, permission_category=permission_category)
    class Entity(views_generator(permission_category)):

        @historical()
        @paginated()
        @filtered_entities()
        @sorted_endpoint()
        @projected()
        @gui_route_logged_in(methods=['GET', 'POST'],
                             required_permission_values={PermissionValue.get(PermissionAction.View,
                                                                             permission_category)})
        def get(self, limit, skip, mongo_filter, mongo_sort,
                mongo_projection, history: datetime):
            # Filter all _preferred fields because they're calculated dynamically, instead filter by original values
            mongo_sort = {x.replace('_preferred', ''): mongo_sort[x] for x in mongo_sort}
            self._save_query_to_history(
                self.entity_type,
                mongo_filter,
                skip,
                limit,
                mongo_sort,
                mongo_projection)
            iterable = get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                    self.entity_type,
                                    default_sort=self._system_settings.get(
                                        'defaultSort'),
                                    history_date=history,
                                    include_details=True)
            return iterator_jsonify(iterable)

        @filtered_entities()
        @gui_route_logged_in(methods=['DELETE'],
                             required_permission_values={PermissionValue.get(PermissionAction.Update,
                                                                             permission_category)})
        def delete_entities(self, mongo_filter):
            return self._delete_entities_by_internal_axon_id(
                self.entity_type, self.get_request_data_as_object(), mongo_filter)

        @historical()
        @filtered_entities()
        @sorted_endpoint()
        @projected()
        @filtered_fields()
        @gui_route_logged_in('csv', methods=['POST'],
                             required_permission_values={PermissionValue.get(PermissionAction.View,
                                                                             permission_category)})
        def get_csv(self, mongo_filter, mongo_sort,
                    mongo_projection, history: datetime, field_filters):

            if 'specific_data.data.image' in mongo_projection:
                del mongo_projection['specific_data.data.image']

            return get_csv_from_heavy_lifting_plugin(mongo_filter,
                                                     mongo_sort,
                                                     mongo_projection,
                                                     history,
                                                     self.entity_type,
                                                     self._system_settings.get(
                                                         'defaultSort'),
                                                     field_filters,
                                                     cell_joiner=self._system_settings.get('cell_joiner'))

        @filtered_entities()
        @historical()
        @gui_route_logged_in('count', methods=['GET', 'POST'],
                             required_permission_values={PermissionValue.get(PermissionAction.View,
                                                                             permission_category)})
        def get_count(self, mongo_filter, history: datetime):
            content = self.get_request_data_as_object()
            quick = content.get('quick') or request.args.get('quick')
            quick = quick == 'True'
            return str(self._get_entity_count(
                self.entity_type, mongo_filter, history, quick))

        @gui_route_logged_in('fields')
        def fields(self):
            return jsonify(entity_fields(self.entity_type))

        @filtered_entities()
        @gui_route_logged_in('labels', methods=['GET'])
        def get_entity_labels(self, mongo_filter):
            db, namespace = (self.devices_db, self.devices) if self.entity_type == EntityType.Devices else \
                (self.users_db, self.users)
            return self._entity_labels(
                db, namespace, mongo_filter)

        @filtered_entities()
        @gui_route_logged_in('labels', methods=['POST', 'DELETE'],
                             required_permission_values={PermissionValue.get(PermissionAction.Update,
                                                                             permission_category)})
        def update_entity_labels(self, mongo_filter):
            db, namespace = (self.devices_db, self.devices) if self.entity_type == EntityType.Devices else \
                (self.users_db, self.users)
            return self._entity_labels(
                db, namespace, mongo_filter)

        @filtered_entities()
        @gui_route_logged_in('disable', methods=['POST'])
        def disable_entity(self, mongo_filter):
            return self._disable_entity(self.entity_type, mongo_filter)

        @filtered_entities()
        @gui_route_logged_in('enforce', methods=['POST'])
        def enforce_entity(self, mongo_filter):
            return self._enforce_entity(self.entity_type, mongo_filter)

        @historical()
        @gui_route_logged_in('<entity_id>', methods=['GET'])
        def entity_generic(self, entity_id, history: datetime):
            res = get_entity_data(self.entity_type, entity_id, history)
            if isinstance(res, dict):
                return jsonify(res)
            return res

        @search_filter()
        @historical()
        @sorted_endpoint()
        @gui_route_logged_in('<entity_id>/<field_name>/csv', methods=['POST'],
                             required_permissions_values={
                                 PermissionValue.get(
                                     PermissionAction.View, permission_category)})
        def entity_generic_field_csv(
                self, entity_id, field_name, mongo_sort, history: datetime, search: str):
            """
            Create a csv file for a specific field of a specific entity

            :param entity_id:   internal_axon_id of the entity to create csv for
            :param field_name:  Field of the entity, containing table data
            :param mongo_sort:  How to sort the table data of the field
            :param history:     Fetch the entity according to this past date
            :param search:      a string to filter the data
            :return:            Response containing csv data, that can be downloaded into a csv file
            """
            csv_string = entity_data_field_csv(self.entity_type, entity_id, field_name,
                                               mongo_sort, history, search_term=search)
            output = make_response(
                (codecs.BOM_UTF8 * 2) + csv_string.getvalue().encode('utf-8'))
            timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
            field_name = field_name.split('.')[-1]
            output.headers[
                'Content-Disposition'] = f'attachment; filename=axonius-data_{field_name}_{timestamp}.csv'
            output.headers['Content-type'] = 'text/csv'
            return output

        @gui_route_logged_in('<entity_id>/tasks', methods=['GET'])
        def entity_tasks(self, entity_id):
            return jsonify(entity_tasks_actions(entity_id))

        @gui_route_logged_in('<entity_id>/notes', methods=['PUT', 'DELETE'],
                             required_permission_values={PermissionValue.get(PermissionAction.Update,
                                                                             permission_category)})
        def entity_notes(self, entity_id):
            return entity_notes(self.entity_type, entity_id,
                                self.get_request_data_as_object())

        @schema()
        @sorted_endpoint()
        @gui_route_logged_in('<entity_id>/tasks/csv', methods=['POST'],
                             required_permission_values={PermissionValue.get(PermissionAction.View,
                                                                             permission_category)})
        def entity_tasks_csv(self, entity_id, mongo_sort, schema_fields):
            """
            Create a csv file for a enforcement tasks of a specific entity

            :param entity_id:   internal_axon_id of the entity tasks to create csv for
            :param mongo_sort:  the sort of the csv
            :param schema_fields:   the fields to show
            :return:            Response containing csv data, that can be downloaded into a csv file
            """
            csv_string = entity_tasks_actions_csv(
                entity_id, schema_fields, mongo_sort)
            output = make_response(csv_string.getvalue().encode('utf-8'))
            timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
            output.headers[
                'Content-Disposition'] = f'attachment; filename=axonius-data_enforcement_tasks_{timestamp}.csv'
            output.headers['Content-type'] = 'text/csv'
            return output

        @gui_route_logged_in('<entity_id>/notes/<note_id>', methods=['POST'],
                             required_permission_values={PermissionValue.get(PermissionAction.Update,
                                                                             permission_category)})
        def entity_notes_update(self, entity_id, note_id):
            return entity_notes_update(self.entity_type, entity_id, note_id,
                                       self.get_request_data_as_object()['note'])

        @filtered_entities()
        @gui_route_logged_in('custom', methods=['POST'],
                             required_permission_values={PermissionValue.get(PermissionAction.Update,
                                                                             permission_category)})
        def entities_custom_data(self, mongo_filter):
            """
            See self._entity_custom_data
            """
            return self._entity_custom_data(self.entity_type, mongo_filter)

        @gui_route_logged_in('hyperlinks')
        def entity_hyperlinks(self):
            return jsonify(self._get_entity_hyperlinks(self.entity_type))

        @filtered_entities()
        @gui_route_logged_in('manual_link', methods=['POST'])
        def entities_link(self, mongo_filter):
            return self._link_many_entities(self.entity_type, mongo_filter)

        @filtered_entities()
        @gui_route_logged_in('manual_unlink', methods=['POST'])
        def entities_unlink(self, mongo_filter):
            return self._unlink_axonius_entities(self.entity_type, mongo_filter)

        @property
        def entity_type(self):
            m = re.search('/api/(.+?)([\\?/].*)?$', request.url)
            if m:
                return EntityType(m.group(1))
            return None

    return Entity
