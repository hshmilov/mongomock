import codecs
import logging
import re
from datetime import datetime
from itertools import islice

from flask import (jsonify,
                   make_response, request)

from axonius.consts.gui_consts import FILE_NAME_TIMESTAMP_FORMAT, ACTIVITY_PARAMS_COUNT, FeatureFlagsNames
from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from axonius.plugin_base import EntityType, return_error
from axonius.utils.db_querying_helper import get_entities
from axonius.utils.gui_helpers import (historical, paginated,
                                       filtered_entities, sorted_endpoint,
                                       projected, filtered_fields,
                                       entity_fields, search_filter,
                                       schema_fields as schema, metadata, return_api_format)
from axonius.utils.json_encoders import iterator_jsonify
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from axonius.utils.threading import GLOBAL_RUN_AND_FORGET
from gui.logic.api_helpers import get_page_metadata
from gui.logic.entity_data import (get_entity_data, entity_data_field_csv,
                                   entity_notes, entity_notes_update, entity_tasks_actions,
                                   entity_tasks_actions_csv)
from gui.logic.generate_csv import get_csv_from_heavy_lifting_plugin
from gui.logic.historical_dates import all_historical_dates
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.routes.entities.views.views_generator import views_generator
from gui.logic.graphql.graphql import allow_experimental, compare_results, compare_counts

# pylint: disable=no-member,no-self-use,too-many-arguments,too-many-statements

logger = logging.getLogger(f'axonius.{__name__}')


def _should_allow_compare(gui):
    return gui.feature_flags_config().get(FeatureFlagsNames.BandicootCompare, False) \
        and gui.feature_flags_config().get(FeatureFlagsNames.ExperimentalAPI, False)


def entity_generator(rule: str, permission_category: PermissionCategory):

    @gui_category_add_rules(rule, permission_category=permission_category)
    class Entity(views_generator(permission_category)):

        @allow_experimental()
        @historical()
        @paginated()
        @filtered_entities()
        @sorted_endpoint()
        @projected()
        @filtered_fields()
        @metadata()
        @gui_route_logged_in(methods=['GET', 'POST'], required_permission=PermissionValue.get(
            PermissionAction.View, permission_category), skip_activity=True)
        def get(self, limit, skip, mongo_filter, mongo_sort,
                mongo_projection, history: datetime,
                field_filters,
                excluded_adapters,
                get_metadata: bool = True,
                include_details: bool = False):
            iterable, cursor_obj = self._get_entities(excluded_adapters, field_filters, history, include_details, limit,
                                                      mongo_filter, mongo_projection, mongo_sort, skip)

            if get_metadata:
                asset_count = self._get_assets_count(
                    entity_type=self.entity_type,
                    mongo_filter=mongo_filter,
                    history_date=history,
                )

                assets = list(iterable)
                page_meta = get_page_metadata(skip=skip, limit=limit, number_of_assets=asset_count)
                page_meta['size'] = len(assets)
                return jsonify({'page': page_meta, 'assets': assets})

            return iterator_jsonify(iterable)

        @allow_experimental()
        @historical()
        @paginated()
        @filtered_entities()
        @sorted_endpoint()
        @projected()
        @filtered_fields()
        @metadata()
        @gui_route_logged_in(rule='cached', methods=['GET', 'POST'], required_permission=PermissionValue.get(
            PermissionAction.View, permission_category), skip_activity=True)
        def get_cached(self, limit, skip, mongo_filter, mongo_sort,
                       mongo_projection, history: datetime,
                       field_filters,
                       excluded_adapters,
                       get_metadata: bool = True,
                       include_details: bool = False):
            iterable, cursor_obj = self._get_entities(excluded_adapters, field_filters, history, include_details, limit,
                                                      mongo_filter, mongo_projection, mongo_sort, skip, use_cursor=True)
            assets = [asset for asset in islice(iterable, limit)]
            if get_metadata:
                page_meta = get_page_metadata(skip=skip,
                                              limit=limit,
                                              number_of_assets=cursor_obj.asset_count,
                                              number=cursor_obj.page_number)
                page_meta['size'] = len(assets)
                return jsonify({'page': page_meta, 'cursor': cursor_obj.cursor_id, 'assets': assets})

            return iterator_jsonify(iterable)

        def _get_entities(self, excluded_adapters, field_filters, history, include_details, limit, mongo_filter,
                          mongo_projection, mongo_sort, skip, use_cursor=False):
            request_data = self.get_request_data_as_object() if request.method == 'POST' else request.args
            # Filter all _preferred fields because they're calculated dynamically, instead filter by original values
            mongo_sort = {x.replace('_preferred', ''): mongo_sort[x] for x in mongo_sort}
            self._save_query_to_history(
                self.entity_type,
                mongo_filter,
                skip,
                limit,
                mongo_sort,
                mongo_projection)
            iterable, cursor_obj = get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                                self.entity_type,
                                                default_sort=self._system_settings.get(
                                                    'defaultSort'),
                                                history_date=history,
                                                include_details=include_details,
                                                field_filters=field_filters,
                                                excluded_adapters=excluded_adapters,
                                                use_cursor=use_cursor,
                                                cursor_id=request_data.get('cursor', None)
                                                )
            # allow compare only if compare flag is on adn ExperimentalAPI is off (we don't execute twice)
            if self.feature_flags_config().get(FeatureFlagsNames.BandicootCompare, False) \
                    and not self.feature_flags_config().get(FeatureFlagsNames.ExperimentalAPI, False):
                iterable = list(iterable)
                logger.info('Executing query compare async')
                # extract request and transfer it to threaded function to compare with bandicoot
                GLOBAL_RUN_AND_FORGET.submit(compare_results, self.entity_type, request_data, iterable)
            return iterable, cursor_obj

        @gui_route_logged_in('history_dates')
        def entities_history_dates(self):
            """Get all of the history dates that are valid for entities."""
            return jsonify(all_historical_dates()[self.entity_type.value])

        @filtered_entities()
        @gui_route_logged_in(methods=['DELETE'], required_permission=PermissionValue.get(PermissionAction.Update,
                                                                                         permission_category),
                             activity_params=[ACTIVITY_PARAMS_COUNT])
        def delete_entities(self, mongo_filter):
            return self._delete_entities_by_internal_axon_id(
                self.entity_type, self.get_request_data_as_object(), mongo_filter)

        @historical()
        @filtered_entities()
        @sorted_endpoint()
        @projected()
        @filtered_fields()
        @gui_route_logged_in('csv', methods=['POST'], required_permission=PermissionValue.get(
            PermissionAction.View, permission_category))
        def get_csv(self, mongo_filter, mongo_sort,
                    mongo_projection, history: datetime, field_filters, excluded_adapters):

            if 'specific_data.data.image' in mongo_projection:
                del mongo_projection['specific_data.data.image']

            delimiter = request.get_json().get('delimiter')
            if delimiter:
                delimiter = delimiter.replace('\\n', '\n')
            max_rows = request.get_json().get('max_rows')

            return get_csv_from_heavy_lifting_plugin(mongo_filter,
                                                     mongo_sort,
                                                     mongo_projection,
                                                     history,
                                                     self.entity_type,
                                                     self._system_settings.get(
                                                         'defaultSort'),
                                                     field_filters,
                                                     excluded_adapters,
                                                     delimiter,
                                                     max_rows)

        @allow_experimental(count=True)
        @filtered_entities()
        @historical()
        @gui_route_logged_in('count', methods=['GET', 'POST'], required_permission=PermissionValue.get(
            PermissionAction.View, permission_category), skip_activity=True)
        def get_count(self, mongo_filter, history: datetime):
            content = self.get_request_data_as_object()
            quick = content.get('quick') or request.args.get('quick')
            quick = quick == 'True'
            mongo_result = str(self._get_entity_count(self.entity_type, mongo_filter, history, quick))
            # allow compare only if compare flag is on adn ExperimentalAPI is off (we don't execute twice)
            if not quick and self.feature_flags_config().get(FeatureFlagsNames.BandicootCompare, False) \
                    and not self.feature_flags_config().get(FeatureFlagsNames.ExperimentalAPI, False):
                logger.info('Executing query count compare async')
                # extract request and transfer it to threaded function to compare with bandicoot
                request_data = self.get_request_data_as_object() if request.method == 'POST' else request.args
                GLOBAL_RUN_AND_FORGET.submit(compare_counts, self.entity_type, request_data, mongo_result)
            return mongo_result

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
        @gui_route_logged_in('labels', methods=['POST', 'DELETE'], required_permission=PermissionValue.get(
            PermissionAction.Update, permission_category))
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
        @return_api_format()
        @gui_route_logged_in('<entity_id>', methods=['GET'])
        def entity_generic(self, entity_id, history: datetime, api_format: bool = True):
            res = get_entity_data(self.entity_type, entity_id, history)
            if isinstance(res, dict):
                if api_format:
                    return jsonify(self.format_entity(entity_id, res))
                return jsonify(res)
            return res

        @search_filter()
        @historical()
        @sorted_endpoint()
        @gui_route_logged_in('<entity_id>/<field_name>/csv', methods=['POST'], required_permission=PermissionValue.get(
            PermissionAction.View, permission_category))
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
            try:
                csv_string = entity_data_field_csv(self.entity_type, entity_id, field_name,
                                                   mongo_sort, history, search_term=search)
            except Exception:
                logger.error('Failed to generate csv from field', exc_info=True)
                return return_error('Failed to generate csv from field', 400)
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

        @gui_route_logged_in('<entity_id>/notes', methods=['PUT', 'DELETE'], required_permission=PermissionValue.get(
            PermissionAction.Update, permission_category))
        def entity_notes(self, entity_id):
            return entity_notes(self.entity_type, entity_id,
                                self.get_request_data_as_object())

        @schema()
        @sorted_endpoint()
        @gui_route_logged_in('<entity_id>/tasks/csv', methods=['POST'], required_permission=PermissionValue.get(
            PermissionAction.View, permission_category))
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

        @gui_route_logged_in('<entity_id>/notes/<note_id>', methods=['POST'], required_permission=PermissionValue.get(
            PermissionAction.Update, permission_category))
        def entity_notes_update(self, entity_id, note_id):
            return entity_notes_update(self.entity_type, entity_id, note_id,
                                       self.get_request_data_as_object()['note'])

        @filtered_entities()
        @gui_route_logged_in('custom', methods=['POST'], required_permission=PermissionValue.get(
            PermissionAction.Update, permission_category))
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
            device_id = self._link_many_entities(self.entity_type, mongo_filter)
            self._trigger_remote_plugin(AGGREGATOR_PLUGIN_NAME, 'calculate_preferred_fields',
                                        blocking=True,
                                        data={'device_ids': [device_id]})
            return device_id

        @filtered_entities()
        @gui_route_logged_in('manual_unlink', methods=['POST'])
        def entities_unlink(self, mongo_filter):
            ret_data = self._unlink_axonius_entities(self.entity_type, mongo_filter)
            self._trigger_remote_plugin_no_blocking(AGGREGATOR_PLUGIN_NAME, 'calculate_preferred_fields')
            return ret_data

        @gui_route_logged_in(rule='destroy', methods=['POST'])
        def api_users_destroy(self):
            """Delete all assets and optionally all historical assets."""
            return self._destroy_assets(entity_type=self.entity_type, historical_prefix='historical_users_')

        @property
        def entity_type(self):
            m = re.search('/api/(.+?)([\\?/].*)?$', request.url)
            if m:
                return EntityType(m.group(1))
            return None

    return Entity
