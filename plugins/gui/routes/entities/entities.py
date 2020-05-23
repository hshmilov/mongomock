import json
import logging
import os
from datetime import datetime
from multiprocessing.pool import ThreadPool
from typing import Dict

import pymongo
from bson import ObjectId
from flask import (jsonify,
                   request)

from axonius.consts.gui_consts import (LAST_UPDATED_FIELD, UPDATED_BY_FIELD,
                                       PREDEFINED_FIELD)
from axonius.consts.metric_consts import Query
from axonius.consts.plugin_consts import (DEVICE_CONTROL_PLUGIN_NAME, PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          REPORTS_PLUGIN_NAME)
from axonius.fields import Field
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import EntityType, return_error
from axonius.types.correlation import (MAX_LINK_AMOUNT, CorrelationReason,
                                       CorrelationResult)
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from axonius.utils.gui_helpers import (add_labels_to_entities,
                                       get_entity_labels, entity_fields, get_connected_user_id,
                                       filtered)
from axonius.utils.mongo_escaping import escape_dict
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.filter_utils import filter_archived
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.logic.views_data import get_views
from gui.routes.entities.entity_generator import entity_generator
# pylint: disable=no-member,inconsistent-return-statements

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules('')
class Entities(entity_generator('devices', PermissionCategory.DevicesAssets),
               entity_generator('users', PermissionCategory.UsersAssets)):

    @staticmethod
    def _insert_view(views_collection, name, mongo_view, description, tags, query_type='saved'):
        existed_view = views_collection.find_one({
            'name': {
                '$regex': name,
                '$options': 'i'
            },
            PREDEFINED_FIELD: True,
            UPDATED_BY_FIELD: '*'
        })
        find_query = {
            '_id': existed_view['_id']
        } if existed_view else {
            'name': name
        }
        current_time = datetime.now()
        views_collection.replace_one(find_query, {
            'name': name,
            'description': description,
            'tags': tags,
            'view': mongo_view,
            'query_type': query_type,
            'timestamp': current_time,
            'user_id': '*',
            UPDATED_BY_FIELD: '*',
            PREDEFINED_FIELD: True
        }, upsert=True)

    def _disable_entity(self, entity_type: EntityType, mongo_filter):
        entity_map = {
            EntityType.Devices: ('Devicedisabelable', 'devices/disable'),
            EntityType.Users: ('Userdisabelable', 'users/disable')
        }
        if entity_type not in entity_map:
            raise Exception('Weird entity type given')

        featurename, urlpath = entity_map[entity_type]

        entities_selection = self.get_request_data_as_object()
        if not entities_selection:
            return return_error('No entity selection provided')
        entity_disabelables_adapters, entity_ids_by_adapters = self._find_entities_by_uuid_for_adapter_with_feature(
            entities_selection, featurename, entity_type, mongo_filter)

        err = ''
        for adapter_unique_name in entity_disabelables_adapters:
            entitys_by_adapter = entity_ids_by_adapters.get(adapter_unique_name)
            if entitys_by_adapter:
                response = self.request_remote_plugin(urlpath, adapter_unique_name, method='POST',
                                                      json=entitys_by_adapter)
                if response.status_code != 200:
                    logger.error(f'Error on disabling on {adapter_unique_name}: {response.content}')
                    err += f'Error on disabling on {adapter_unique_name}: {response.content}\n'

        return return_error(err, 500) if err else ('', 200)

    def _find_entities_by_uuid_for_adapter_with_feature(self, entities_selection, feature, entity_type: EntityType,
                                                        mongo_filter):
        """
        Find all entity from adapters that have a given feature, from a given set of entities
        :return: plugin_unique_names of entity with given features, dict of plugin_unique_name -> id of adapter entity
        """
        db_connection = self._get_db_connection()
        query_op = '$in' if entities_selection['include'] else '$nin'
        entities = list(self._entity_db_map.get(entity_type).find({
            '$and': [
                {'internal_axon_id': {
                    query_op: entities_selection['ids']
                }}, mongo_filter
            ]}))
        entities_ids_by_adapters = {}
        for axonius_device in entities:
            for adapter_entity in axonius_device['adapters']:
                entities_ids_by_adapters.setdefault(adapter_entity[PLUGIN_UNIQUE_NAME], []).append(
                    adapter_entity['data']['id'])

                # all adapters that are disabelable and that theres atleast one
                entitydisabelables_adapters = [x[PLUGIN_UNIQUE_NAME]
                                               for x in
                                               db_connection['core']['configs'].find(
                                                   filter={
                                                       'supported_features': feature,
                                                       PLUGIN_UNIQUE_NAME: {
                                                           '$in': list(entities_ids_by_adapters.keys())
                                                       }
                                                   },
                                                   projection={
                                                       PLUGIN_UNIQUE_NAME: 1
                                                   })]
        return entitydisabelables_adapters, entities_ids_by_adapters

    def _enforce_entity(self, entity_type: EntityType, mongo_filter):
        """
        Trigger selected Enforcement with a static list of entities, as selected by user
        """
        post_data = self.get_request_data_as_object()
        self._trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'run', blocking=False, data={
            'report_name': post_data.pop('name', ''),
            'input': {
                'entity': entity_type.name,
                'filter': escape_dict(mongo_filter),
                'selection': post_data
            }
        })
        return '', 200

    @staticmethod
    def _get_entity_views(entity_type: EntityType, limit, skip, mongo_filter, mongo_sort, query_type='saved'):
        """
        get entity views
        :return:
        """
        mongo_filter['query_type'] = query_type
        return [beautify_db_entry(entry)
                for entry
                in get_views(entity_type, limit, skip, mongo_filter, mongo_sort)]

    def _add_entity_view(self, entity_type: EntityType):
        """
        Save or fetch views over the entities db
        :return:
        """
        entity_views_collection = self.gui_dbs.entity_query_views_db_map[entity_type]
        view_data = self.get_request_data_as_object()
        tags = view_data.get('tags', [])

        if not view_data.get('name'):
            return return_error(f'Name is required in order to save a view', 400)
        if not view_data.get('view'):
            return return_error(f'View data is required in order to save one', 400)
        view_to_update = {
            'name': view_data['name'],
            'description': view_data.get('description', ''),
            'view': view_data['view'],
            'query_type': 'saved',
            'tags': tags,
            'archived': False,
        }
        if view_data.get(PREDEFINED_FIELD):
            view_to_update[PREDEFINED_FIELD] = view_data[PREDEFINED_FIELD]
        if not self.is_axonius_user():
            view_to_update[LAST_UPDATED_FIELD] = datetime.now()
            view_to_update[UPDATED_BY_FIELD] = get_connected_user_id()
            view_to_update['user_id'] = get_connected_user_id()
        update_result = entity_views_collection.find_one_and_update({
            'name': view_data['name']
        }, {
            '$set': view_to_update
        }, upsert=True, return_document=pymongo.ReturnDocument.AFTER)

        return str(update_result['_id'])

    def _delete_entity_views(self, entity_type: EntityType, mongo_filter) -> int:
        entity_views_collection = self.gui_dbs.entity_query_views_db_map[entity_type]

        selection = self.get_request_data_as_object()
        selection['ids'] = [ObjectId(i) for i in selection['ids']]
        query_ids = self.get_selected_ids(entity_views_collection, selection, mongo_filter)
        update_result = entity_views_collection.update_many({
            '_id': {
                '$in': query_ids
            }
        }, {
            '$set': {
                'archived': True
            }
        })
        return update_result.modified_count

    def _update_entity_views(self, entity_type: EntityType, query_id):
        view_data = self.get_request_data_as_object()
        if not view_data.get('name'):
            return return_error(f'Name is required in order to save a view', 400)
        view_set_data = {
            'name': view_data['name'],
            'view': view_data['view'],
        }
        if 'description' in view_data:
            view_set_data['description'] = view_data.get('description', '')
        if 'tags' in view_data:
            view_set_data['tags'] = view_data.get('tags', [])
        if not self.is_axonius_user():
            view_set_data[LAST_UPDATED_FIELD] = datetime.now()
            view_set_data[UPDATED_BY_FIELD] = get_connected_user_id()
        self.gui_dbs.entity_query_views_db_map[entity_type].update_one({
            '_id': ObjectId(query_id)
        }, {
            '$set': view_set_data
        })

    def _get_queries_tags_by_entity(self, entity_type):
        """
        Find all tags that assigned to users/devices saved queries and return them as a distinct list
        :param entity_type: users/devices
        :return: distinct list of tags
        """
        return self.gui_dbs.entity_query_views_db_map[entity_type].distinct('tags')

    def _get_queries_names_by_entity(self, entity_type):
        """
        Return a list of all existing saved-queries names in system for a specific entity type
        :param entity_type: users / devices
        :return: list of saved-queries names
        """
        not_archived_saved_queries = filter_archived({'query_type': 'saved'})
        return self.gui_dbs.entity_query_views_db_map[entity_type].find(
            not_archived_saved_queries, {'name': 1, '_id': 0}
        )

    def _entity_labels(self, db, namespace, mongo_filter):
        """
        GET Find all tags that currently belong to devices, to form a set of current tag values
        POST Add new tags to the list of given devices
        DELETE Remove old tags from the list of given devices
        :return:
        """
        if request.method == 'GET':
            return jsonify(get_entity_labels(db))

        # Now handling POST and DELETE - they determine if the label is an added or removed one
        entities_and_labels = self.get_request_data_as_object()
        if not entities_and_labels.get('entities'):
            return return_error('Cannot label entities without list of entities.', 400)
        if not entities_and_labels.get('labels'):
            return return_error('Cannot label entities without list of labels.', 400)
        try:
            select_include = entities_and_labels['entities'].get('include', True)
            select_ids = entities_and_labels['entities'].get('ids', [])
            internal_axon_ids = select_ids if select_include else [entry['internal_axon_id'] for entry in db.find({
                '$and': [
                    mongo_filter, {
                        'internal_axon_id': {
                            '$nin': select_ids
                        }
                    }
                ]
            }, projection={'internal_axon_id': 1})]
            add_labels_to_entities(namespace,
                                   internal_axon_ids,
                                   entities_and_labels['labels'],
                                   request.method == 'DELETE')
        except Exception as e:
            logger.exception(f'Tagging did not complete')
            return return_error(f'Tagging did not complete. First error: {e}', 400)

        return str(len(internal_axon_ids)), 200

    def _delete_entities_by_internal_axon_id(self, entity_type: EntityType, entities_selection, mongo_filter):
        entities = self._entity_db_map[entity_type].find({
            'internal_axon_id': {
                '$in': self.get_selected_entities(entity_type, entities_selection, mongo_filter)
            }
        }, projection={
            f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
            f'adapters.data.id': 1
        })
        raw_col = self._raw_adapter_entity_db_map[entity_type]
        with ThreadPool(15) as pool:
            def delete_raw(axonius_entity):
                for adapter in axonius_entity['adapters']:
                    raw_col.delete_one({
                        PLUGIN_UNIQUE_NAME: adapter[PLUGIN_UNIQUE_NAME],
                        'id': adapter['data']['id']
                    })
            pool.map(delete_raw, entities)
        deleted_result = self._entity_db_map[entity_type].delete_many({
            'internal_axon_id': {
                '$in': self.get_selected_entities(entity_type, entities_selection, mongo_filter)
            }
        })
        self._trigger('clear_dashboard_cache', blocking=False)

        return jsonify({'count': deleted_result.deleted_count})

    def _save_query_to_history(self, entity_type: EntityType, view_filter, skip, limit, sort, projection):
        """
        After a query (e.g. find all devices) has been made in the GUI we want to save it in the history
        for the user's comfort.
        :param entity_type: The type of the entity queried
        :param view_filter: the filter passed by @filtered
        :param skip: the "skip" used by the user from @paginated()
        :param limit: the "limit" used by the users from @paginated()
        :param sort: the "sort" from @sorted_endpoint()
        :param projection: the "mongo_projection" from @projected()
        :return: None
        """
        if self.is_axonius_user():
            return

        view_filter = request.args.get('filter')
        if request.args.get('is_refresh') != '1':
            log_metric(logger, Query.QUERY_GUI, view_filter)
            history = request.args.get('history')
            if history:
                log_metric(logger, Query.QUERY_HISTORY, str(history))

        if view_filter and not skip:
            # getting the original filter text on purpose - we want to pass it
            mongo_sort = {'desc': -1, 'field': ''}
            if sort:
                field, desc = next(iter(sort.items()))
                mongo_sort = {'desc': int(desc), 'field': field}
            self.gui_dbs.entity_query_views_db_map[entity_type].replace_one(
                {'name': {'$exists': False}, 'view.query.filter': view_filter},
                {
                    'view': {
                        'page': 0,
                        'fields': list((projection or {}).keys()),
                        'coloumnSizes': [],
                        'query': {
                            'filter': view_filter,
                            'expressions': json.loads(request.args.get('expressions', '[]'))
                        },
                        'sort': mongo_sort
                    },
                    'query_type': 'history',
                    'timestamp': datetime.now()
                },
                upsert=True)

    def _entity_custom_data(self, entity_type: EntityType, mongo_filter=None):
        """
        Adds misc adapter data to the data as given in the request
        POST data:
        {
            'selection': {
                'ids': list of ids, 'include': true / false
            },
            'data': {...}
        }
        For each field to set, search for as a title of an existing field.
        If found, set matching value to that field.
        Otherwise, create a new field with the name as a title and 'custom_<name>' as the field name.

        :param entity_type: the entity type to use
        """
        post_data = request.get_json()
        entities = list(self._entity_db_map[entity_type].find(filter={
            'internal_axon_id': {
                '$in': self.get_selected_entities(entity_type, post_data['selection'], mongo_filter)
            }
        }, projection={
            'internal_axon_id': True,
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
            'adapters.data.id': True
        }))

        entity_to_add = self._new_device_adapter() if entity_type == EntityType.Devices else self._new_user_adapter()

        errors = {}
        for k, v in post_data['data'].items():
            if not isinstance(v, (str, int, bool, float)):
                errors[k] = f'{k} is of type {type(v)} which is not allowed'
            try:
                if k.startswith('custom_'):
                    entity_to_add.set_static_field(k, Field(type(v), k))
                elif not entity_to_add.set_field_by_title(k, v):
                    # Canonize field name with title as received
                    field_name = f'custom_{"_".join(k.split(" ")).lower()}'
                    entity_to_add.declare_new_field(field_name, Field(type(v), k))
                    setattr(entity_to_add, field_name, v)
            except Exception:
                errors[k] = f'Value {v} not compatible with field {k}'
                logger.exception(errors[k])

        if len(errors) > 0:
            return return_error(errors, 400)

        entity_to_add_dict = entity_to_add.to_dict()

        with ThreadPool(5) as pool:
            def tag_adapter(entity):
                try:
                    self.add_adapterdata_to_entity(entity_type,
                                                   [(x[PLUGIN_UNIQUE_NAME], x['data']['id'])
                                                    for x
                                                    in entity['adapters']],
                                                   entity_to_add_dict,
                                                   action_if_exists='update')
                except Exception as e:
                    logger.exception(e)

            pool.map(tag_adapter, entities)

        self._save_field_names_to_db(entity_type)
        self._trigger('clear_dashboard_cache', blocking=False)
        entity_fields.clean_cache()
        return '', 200

    def _get_entity_hyperlinks(self, entity_type: EntityType) -> Dict[str, str]:
        """
        Get all hyperlinks codes from all adapters for the given entity type
        :return: dict between the plugin_name and the JS code all entities
        """
        collection = self._all_fields_db_map[entity_type]
        documents = collection.find({
            'name': 'hyperlinks'
        }, projection={
            PLUGIN_NAME: 1,
            'code': 1
        })
        return {x[PLUGIN_NAME]: x['code'] for x in documents}

    def _link_many_entities(self, entity_type: EntityType, mongo_filter):
        """
        Link many given entities
        :param entity_type: the entity type
        :param mongo_filter: The mongo filter to use
        :return: The internal_axon_id of the new entity
        """
        post_data = request.get_json()
        internal_axon_ids = self.get_selected_entities(entity_type, post_data, mongo_filter)
        if len(internal_axon_ids) > MAX_LINK_AMOUNT:
            return return_error(f'Maximal amount of entities to link at once is {MAX_LINK_AMOUNT}')
        if len(internal_axon_ids) < 2:
            return return_error('Please choose at least two entities to link')
        correlation = CorrelationResult(associated_adapters=[], data={
            'reason': 'User correlated those',
            'original_entities': internal_axon_ids,
            'user_id': get_connected_user_id()
        }, reason=CorrelationReason.UserManualLink)
        return self.link_adapters(entity_type, correlation, entities_candidates_hint=list(internal_axon_ids))

    def _unlink_axonius_entities(self, entity_type: EntityType, mongo_filter):
        """
        "Shatters" an axonius entity: Creates many axonius entities from each of the adapters entities.
        :param entity_type: the entity type
        :param mongo_filter: Which entities to run on
        """
        entities_selection = self.get_request_data_as_object()
        if not entities_selection:
            return return_error('No entity selection provided')
        db = self._entity_db_map[entity_type]
        projection = {
            'adapters.data.id': 1,
            f'adapters.{PLUGIN_UNIQUE_NAME}': 1
        }
        if entities_selection['include']:
            entities = db.find({
                'internal_axon_id': {
                    '$in': entities_selection['ids']
                }
            }, projection=projection)
        else:
            entities = db.find({
                '$and': [
                    {'internal_axon_id': {
                        '$nin': entities_selection['ids']
                    }}, mongo_filter
                ]
            }, projection=projection)

        for entity in entities:
            adapters = entity['adapters']
            if len(adapters) < 2:
                continue
            for adapter in adapters[:-1]:
                # Unlink all adapters except the last
                self.unlink_adapter(entity_type, adapter[PLUGIN_UNIQUE_NAME], adapter['data']['id'])

        return ''

    def run_actions(self, action_data, mongo_filter):
        # The format of data is defined in device_control\service.py::run_shell
        action_type = action_data['action_type']
        entities_selection = action_data['entities']
        action_data['internal_axon_ids'] = entities_selection['ids'] if entities_selection['include'] else [
            entry['internal_axon_id'] for entry in self.devices_db.find({
                '$and': [
                    mongo_filter, {
                        'internal_axon_id': {
                            '$nin': entities_selection['ids']
                        }
                    }
                ]
            }, projection={'internal_axon_id': 1})]
        del action_data['entities']

        try:
            if 'action_name' not in action_data or ('command' not in action_data and 'binary' not in action_data):
                return return_error('Some data is missing')

            self._trigger_remote_plugin(DEVICE_CONTROL_PLUGIN_NAME, priority=True, blocking=False,
                                        data=action_data)
            return '', 200
        except Exception as e:
            return return_error(f'Attempt to run action {action_type} caused exception. Reason: {repr(e)}'
                                if os.environ.get('PROD') == 'false' else
                                f'Attempt to run action {action_type} caused exception.', 400)

    @filtered()
    @gui_route_logged_in('actions/<action_type>', methods=['POST'], required_permission=PermissionValue.get(
        PermissionAction.Update, PermissionCategory.DevicesAssets))
    def actions_run(self, action_type, mongo_filter):
        action_data = self.get_request_data_as_object()
        action_data['action_type'] = action_type
        return self.run_actions(action_data, mongo_filter)
