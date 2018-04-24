import io
import csv
import logging

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME

logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterProperty

from axonius.utils.files import get_local_config_file
from axonius.plugin_base import PluginBase, add_rule, return_error, EntityType
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.consts import plugin_consts
from axonius.consts.scheduler_consts import ResearchPhases, StateLevels, Phases

import tarfile
import io
import os
from datetime import date
from flask import jsonify, request, session, after_this_request, make_response
from passlib.hash import bcrypt
from elasticsearch import Elasticsearch
import requests
import configparser
import pymongo
from bson import ObjectId
import json
from datetime import datetime
from axonius.utils.parsing import parse_filter
import re

# the maximal amount of data a pagination query will give
PAGINATION_LIMIT_MAX = 2000


def add_rule_unauthenticated(rule, require_connected=True, *args, **kwargs):
    """
    Syntactic sugar for add_rule(should_authenticate=False, ...)
    :param rule: rule name
    :param require_connected: whether or not to require that the user is connected
    :param args:
    :param kwargs:
    :return:
    """
    add_rule_res = add_rule(rule, should_authenticate=False, *args, **kwargs)
    if require_connected:
        return lambda func: requires_connected(add_rule_res(func))
    return add_rule_res


# Caution! These decorators must come BEFORE @add_rule


def requires_connected(func):
    """
    Decorator stating that the view requires the user to be connected
    """

    def wrapper(self, *args, **kwargs):
        user = session.get('user')
        if user is None:
            return return_error("You're not connected", 401)
        return func(self, *args, **kwargs)

    return wrapper


# Caution! These decorators must come BEFORE @add_rule


def gzipped_downloadable(filename, extension):
    filename = filename.format(date.today())

    def gzipped_downloadable_wrapper(f):
        def view_func(*args, **kwargs):
            @after_this_request
            def zipper(response):
                response.direct_passthrough = False

                if (response.status_code < 200 or
                        response.status_code >= 300 or
                        'Content-Encoding' in response.headers):
                    return response
                uncompressed = io.BytesIO(response.data)
                compressed = io.BytesIO()

                tar = tarfile.open(mode='w:gz', fileobj=compressed)
                tarinfo = tarfile.TarInfo(f"{filename}.{extension}")
                tarinfo.size = len(response.data)
                tar.addfile(tarinfo, fileobj=uncompressed)
                tar.close()

                response.data = compressed.getbuffer()
                if "Content-Disposition" not in response.headers:
                    response.headers["Content-Disposition"] = f"attachment;filename={filename}.tar.gz"
                return response

            return f(*args, **kwargs)

        return view_func

    return gzipped_downloadable_wrapper


# Caution! These decorators must come BEFORE @add_rule
def paginated(limit_max=PAGINATION_LIMIT_MAX):
    """
    Decorator stating that the view supports "?limit=X&start=Y" for pagination
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            # it's fine to raise here - an exception will be nicely JSONly displayed by add_rule
            limit = request.args.get('limit', limit_max, int)
            if limit < 0:
                raise ValueError("Limit mustn't be negative")
            if limit > limit_max:
                limit = limit_max
            skip = int(request.args.get('skip', 0, int))
            if skip < 0:
                raise ValueError("start mustn't be negative")
            return func(self, limit=limit, skip=skip, *args, **kwargs)

        return actual_wrapper

    return wrap


# Caution! These decorators must come BEFORE @add_rule
def filtered():
    """
    Decorator stating that the view supports ?filter='adapters == "active_directory_adapter"'
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            filter_obj = dict()
            try:
                filter_expr = request.args.get('filter')
                if filter_expr:
                    logger.debug("Parsing filter: {0}".format(filter_expr))
                    filter_obj = parse_filter(filter_expr)
            except Exception as e:
                return return_error("Could not create mongo filter. Details: {0}".format(e), 400)
            return func(self, mongo_filter=filter_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


def sorted():
    """
    Decorator stating that the view supports ?sort=<field name><'-'/'+'>
    The field name must match a field in the collection to sort by
    and the -/+ determines whether sort is descending or ascending
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            sort_obj = {}
            try:
                sort_param = request.args.get('sort')
                if sort_param:
                    logger.debug(f'Parsing sort: {sort_param}')
                    sort_field = sort_param[:-1]
                    sort_direction = sort_param[-1]
                    sort_obj[sort_field] = pymongo.DESCENDING if (sort_direction == '-') else pymongo.ASCENDING
            except Exception as e:
                return return_error("Could not create mongo sort. Details: {0}".format(e), 400)
            return func(self, mongo_sort=sort_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


# Caution! These decorators must come BEFORE @add_rule
def projectioned():
    """
    Decorator stating that the view supports ?fields=["name","hostname",["os_type":"OS.type"]]
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            fields = request.args.get('fields')
            mongo_fields = None
            if fields:
                try:
                    mongo_fields = {}
                    for field in fields.split(","):
                        mongo_fields[field] = 1
                except json.JSONDecodeError:
                    pass
            return func(self, mongo_projection=mongo_fields, *args, **kwargs)

        return actual_wrapper

    return wrap


def beautify_db_entry(entry):
    """
    Renames the '_id' to 'date_fetched', and stores it as an id to 'uuid' in a dict from mongo
    :type entry: dict
    :param entry: dict from mongodb
    :return: dict
    """
    tmp = {**entry, **{'date_fetched': entry['_id']}}
    tmp['uuid'] = str(entry['_id'])
    del tmp['_id']
    return tmp


def filter_archived():
    return {'$or': [{'archived': {'$exists': False}}, {'archived': False}]}


class GuiService(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)
        self.wsgi_app.config['SESSION_TYPE'] = 'memcached'
        self.wsgi_app.config['SECRET_KEY'] = 'this is my secret key which I like very much, I have no idea what is this'
        self._elk_addr = self.config['gui_specific']['elk_addr']
        self._elk_auth = self.config['gui_specific']['elk_auth']
        self.db_user = self.config['gui_specific']['db_user']
        self.db_password = self.config['gui_specific']['db_password']
        self._get_collection('users', limited_user=False).update({'user_name': 'admin'},
                                                                 {'user_name': 'admin',
                                                                  'first_name': 'administrator',
                                                                  'last_name': '',
                                                                  'pic_name': 'avatar.png',
                                                                  'password': bcrypt.hash('bestadminpassword')},
                                                                 upsert=True)
        self.add_default_queries('device', 'default_queries_devices.ini')
        self.add_default_queries('user', 'default_queries_users.ini')

    def add_default_queries(self, module_name, default_queries_ini_path):
        """
        Adds default queries.
        :param module_name: "device" or "user"
        :param default_queries_ini_path: the file path with the queries
        :return:
        """
        # Load default queries and save them to the DB
        try:
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), default_queries_ini_path)))

            # Save default queries
            for name, query in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    self._insert_query(module_name, name, query['query'])
                except Exception:
                    logger.exception(f'Error adding default query {name}')
        except Exception:
            logger.exception(f'Error adding default queries')

    def _insert_query(self, module_name, name, query_filter, query_expressions=[]):
        queries_collection = self._get_collection(f'{module_name}_queries', limited_user=False)
        existed_query = queries_collection.find_one({'filter': query_filter, 'name': name})
        if existed_query is not None and not existed_query.get('archived'):
            logger.info(f'Query {name} already exists id: {existed_query["_id"]}')
            return existed_query['_id']
        result = queries_collection.update({'name': name}, {'$set': {'name': name, 'filter': query_filter,
                                                                     'expressions': query_expressions,
                                                                     'query_type': 'saved', 'timestamp': datetime.now(),
                                                                     'archived': False}}, upsert=True)
        logger.info(f'Added query {name} id: {result.get("inserted_id", "")}')
        return result.get('inserted_id', '')

    ########
    # DATA #
    ########

    def _get_entities(self, limit, skip, filter, sort, projection, module_name):
        """
        Get Axonius data of type <module_name>, from the aggregator which is expected to store them.
        """
        logger.debug(f'Fetching data for module {module_name}')
        with self._get_db_connection(False) as db_connection:
            pipeline = [{'$match': filter}]
            if projection:
                projection['internal_axon_id'] = 1
                projection['adapters'] = 1
                projection['unique_adapter_names'] = 1
                projection['labels'] = 1
                pipeline.append({'$project': projection})
            if sort:
                pipeline.append({'$sort': sort})
            else:
                # Default sort by adapters list size and then Mongo id (giving order of insertion)
                pipeline.append({'$addFields': {'adapters_size': {'$size': '$adapters'}}})
                pipeline.append({'$sort': {'adapters_size': pymongo.DESCENDING, '_id': pymongo.DESCENDING}})
            if skip:
                pipeline.append({'$skip': skip})
            if limit:
                pipeline.append({'$limit': limit})

            # Fetch from Mongo is done with aggregate, for the purpose of setting 'allowDiskUse'.
            # The reason is that sorting without the flag, causes exceeding of the memory limit.
            data_list = db_connection[plugin_consts.AGGREGATOR_PLUGIN_NAME][f'{module_name}s_db_view'].aggregate(
                pipeline, allowDiskUse=True)

            if filter and not skip:
                filter = request.args.get('filter')
                db_connection[self.plugin_unique_name][f'{module_name}_queries'].replace_one(
                    {'name': {'$exists': False}, 'filter': filter},
                    {'filter': filter, 'query_type': 'history', 'timestamp': datetime.now(), 'archived': False},
                    upsert=True)
            if not projection:
                return [beautify_db_entry(entity) for entity in data_list]
            return [self._parse_entity_fields(entity, projection.keys()) for entity in data_list]

    def _parse_entity_fields(self, entity_data, fields):
        """
        For each field in given list, if it begins with adapters_data, just fetch it from corresponding adapter.

        :param entity_data: A nested dict representing parsed values of an entity
        :param fields:      List of paths to values in the entity_data dict
        :return:            Mapping of a field path to it's value list as found in the entity_data
        """
        field_to_value = {}
        for field in fields:
            field_to_value[field] = self._find_entity_field(entity_data, field)
        return field_to_value

    def _find_entity_field(self, entity_data, field_path):
        """
        Recursively expand given entity, following period separated properties of given field_path,
        until reaching the requested value

        :param entity_data: A nested dict representing parsed values of an entity
        :param field_path:  A path to a field ('.' separated chain of keys)
        :return:
        """
        if entity_data is None:
            # Return no value for this path
            return ''
        if not field_path:
            # Return value corresponding with given path
            return entity_data

        if type(entity_data) != list:
            first_dot = field_path.find('.')
            if first_dot == -1:
                # Return value of last key in the chain
                return entity_data.get(field_path)
            # Continue recursively with value of current key and rest of path
            return self._find_entity_field(entity_data.get(field_path[:first_dot]), field_path[first_dot + 1:])

        if len(entity_data) == 1:
            # Continue recursively on the single element in the list, with the same path
            return self._find_entity_field(entity_data[0], field_path)

        children = []
        for item in entity_data:
            # Continue recursively for current element of the list
            child_value = self._find_entity_field(item, field_path)
            if child_value:
                def new_instance(value):
                    """
                    Test if given value is not yet found in the children list, according to comparison rules.
                    For strings, if value is a prefix of or has a prefix in the list, is considered to be found.
                    :param value:   Value for testing if exists in the list
                    :return: True, if value is new to the children list and False otherwise
                    """
                    def same_string(x, y): return type(x) != 'str' or (re.match(x, y, re.I) or re.match(y, x, re.I))
                    if type(value) == str:
                        return len([child for child in children if same_string(child, value)]) == 0
                    if type(value) == int:
                        return value in children
                    if type(value) == dict:
                        # For a dict, check if there is an element of whom all keys are identical to value's keys
                        return len([item for item in children if len([key for key in item.keys()
                                                                      if same_string(item[key], value[key])]) > 0]) == 0
                    return False

                if type(child_value) == list:
                    # Check which elements of found value can be added to children
                    children = children + list(filter(new_instance, child_value))
                elif new_instance(child_value):
                    # Check if value found can be added to children
                    children.append(child_value)

        return children

    def _get_csv(self, mongo_filter, mongo_sort, mongo_projection, module_name):
        """
        Given a module_name, retrieve it's entities, according to given filter, sort and requested fields.
        The resulting list is processed into csv format and returned as a file content, to be downloaded by browser.

        :param mongo_filter:
        :param mongo_sort:
        :param mongo_projection:
        :param module_name:
        :return:
        """
        logger.info("Generating csv")
        string_output = io.StringIO()
        entities = self._get_entities(None, None, mongo_filter, mongo_sort, mongo_projection, module_name)
        output = ''
        if len(entities) > 0:
            # Beautifying the resulting csv.
            del mongo_projection['internal_axon_id']
            del mongo_projection['unique_adapter_names']
            # Getting pretty titles for all generic fields as well as specific
            entity_fields = self._entity_fields(module_name)
            for field in entity_fields['generic']:
                if field['name'] in mongo_projection:
                    mongo_projection[field['name']] = field['title']
            for type in entity_fields['specific']:
                for field in entity_fields['specific'][type]:
                    if field['name'] in mongo_projection:
                        mongo_projection[field['name']] = field['title']

            for current_entity in entities:
                del current_entity['internal_axon_id']
                del current_entity['unique_adapter_names']
                for field in mongo_projection.keys():
                    # Replace field paths with their pretty titles
                    if field in current_entity:
                        current_entity[mongo_projection[field]] = current_entity[field]
                        del current_entity[field]
            dw = csv.DictWriter(string_output, mongo_projection.values())
            dw.writeheader()
            dw.writerows(entities)
            output = make_response(string_output.getvalue())
            output.headers["Content-Disposition"] = "attachment; filename=export.csv"
            output.headers["Content-type"] = "text/csv"
        return output

    def _entity_by_id(self, module_name, entity_id, advanced_fields=[]):
        """
        Retrieve device by the given id, from current devices DB or update it
        Currently, update works only for tags because that is the only edit operation user has
        :return:
        """
        def _basic_generic_field_names():
            generic_field_names = list(map(lambda field: field.get(
                'name'), self._entity_fields(module_name)['generic']))
            return filter(
                lambda field: field != 'adapters' and field != 'labels' and
                len([category for category in advanced_fields if category in field]) == 0,
                generic_field_names)

        with self._get_db_connection(False) as db_connection:
            entity = db_connection[plugin_consts.AGGREGATOR_PLUGIN_NAME][f'{module_name}s_db_view'].find_one(
                {'internal_axon_id': entity_id})
            if entity is None:
                return return_error("Entity ID wasn't found", 404)
            # Specific is returned as is, to show all adapter datas.
            # Generic fields are divided to basic which are all merged through all adapter datas
            # and advanced, of which the main field is merged and data is given in original structure.
            return jsonify({
                'specific': entity['specific_data'],
                'generic': {
                    'basic': self._parse_entity_fields(entity, _basic_generic_field_names()),
                    'advanced': [{
                        'name': category, 'data': self._find_entity_field(entity, f'specific_data.data.{category}')
                    } for category in advanced_fields],
                    'data': entity['generic_data']
                },
                'labels': entity['labels'],
                'internal_axon_id': entity['internal_axon_id']
            })

    def _entity_queries(self, limit, skip, filter, module_name):
        """
                GET Fetch all queries saved for given module, answering give filter
                POST Save a new query for given module
                     Data with a name for the query and a string filter is expected for saving

                :param limit: limit for pagination
                :param skip: start index for pagination
                :return: GET - List of query names and filters
                         POST - Id of inserted document saving given query
                """
        if request.method == 'GET':
            filter['$or'] = filter_archived()['$or']
            queries_collection = self._get_collection(f'{module_name}_queries', limited_user=False)
            return jsonify(beautify_db_entry(entry) for entry in queries_collection.find(filter)
                           .sort([('timestamp', pymongo.DESCENDING)])
                           .skip(skip).limit(limit))
        if request.method == 'POST':
            query_to_add = request.get_json(silent=True)
            if query_to_add is None or query_to_add['filter'] == '':
                return return_error("Invalid query", 400)
            inserted_id = self._insert_query(module_name, query_to_add.get('name'), query_to_add.get('filter'),
                                             query_to_add.get('expressions'))
            return str(inserted_id), 200

    def _entity_queries_delete(self, module_name, query_id):
        queries_collection = self._get_collection(f'{module_name}_queries', limited_user=False)
        queries_collection.update({'_id': ObjectId(query_id)},
                                  {
                                      '$set': {
                                          'archived': True
                                      }}
                                  )
        return ""

    def _get_entities_count(self, filter, module_name):
        """
        Count total number of devices answering given mongo_filter

        :param filter: Object defining a Mongo query
        :return: Number of devices
        """
        with self._get_db_connection(False) as db_connection:
            data_collection = db_connection[plugin_consts.AGGREGATOR_PLUGIN_NAME][f'{module_name}s_db_view']
            return str(data_collection.find(filter, {'_id': 1}).count())

    def _flatten_fields(self, schema, name='', exclude=[]):
        def _merge_title(schema, title):
            """
            If exists, add given title before that of given schema or set it if none existing
            :param schema:
            :param title:
            :return:
            """
            new_schema = {**schema}
            if title:
                new_schema['title'] = f'{title} {new_schema["title"]}' if new_schema.get('title') else title
            return new_schema

        if (schema.get('name')):
            if schema['name'] in exclude:
                return []
            name = f'{name}.{schema["name"]}' if name else schema['name']

        if schema['type'] == 'array' and schema.get('items'):
            if type(schema['items']) == list:
                children = []
                for item in schema['items']:
                    if not item.get('title'):
                        continue
                    children = children + self._flatten_fields(_merge_title(item, schema.get('title')), name)
                return children

            if schema['items']['type'] != 'array':
                if not schema.get('title'):
                    return []
                return [{**schema, 'name': name}]
            return self._flatten_fields(_merge_title(schema['items'], schema.get('title')), name, exclude)

        if not schema.get('title'):
            return []
        return [{**schema, 'name': name}]

    def _entity_fields(self, module_name):
        """
        Get generic fields schema as well as adapter-specific parsed fields schema.
        Together these are all fields that any device may have data for and should be presented in UI accordingly.

        :return:
        """
        def _get_generic_fields():
            if module_name == 'device':
                return DeviceAdapter.get_fields_info()
            elif module_name == 'user':
                return UserAdapter.get_fields_info()
            return dict()

        all_supported_properties = [x.name for x in AdapterProperty.__members__.values()]

        generic_fields = _get_generic_fields()
        fields = {
            'schema': {'generic': generic_fields, 'specific': {}},
            'generic': [{
                'name': 'adapters', 'title': 'Adapters', 'type': 'array', 'items': {
                    'type': 'string', 'format': 'logo', 'enum': []
                }}, {
                'name': 'specific_data.adapter_properties', 'title': 'Adapter Properties', 'type': 'string',
                'enum': all_supported_properties
            }] + self._flatten_fields(generic_fields, 'specific_data.data', ['scanner']) + [{
                'name': 'labels', 'title': 'Tags', 'type': 'array', 'items': {'type': 'string', 'format': 'tag'}
            }],
            'specific': {}
        }
        plugins_available = requests.get(self.core_address + '/register').json()
        with self._get_db_connection(False) as db_connection:
            plugins_from_db = list(db_connection['core']['configs'].find({}).
                                   sort([(plugin_consts.PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)]))
            for plugin in plugins_from_db:
                if not plugin[plugin_consts.PLUGIN_UNIQUE_NAME] in plugins_available:
                    continue
                plugin_fields = db_connection[plugin[plugin_consts.PLUGIN_UNIQUE_NAME]][f'{module_name}_fields']
                if not plugin_fields:
                    continue
                plugin_fields_record = plugin_fields.find_one({'name': 'parsed'}, projection={'schema': 1})
                if not plugin_fields_record:
                    continue
                fields['schema']['specific'][plugin[plugin_consts.PLUGIN_NAME]] = plugin_fields_record['schema']
                fields['specific'][plugin[plugin_consts.PLUGIN_NAME]] = self._flatten_fields(
                    plugin_fields_record['schema'], f'adapters_data.{plugin[plugin_consts.PLUGIN_NAME]}', ['scanner'])

        return fields

    def _disable_entity(self, entity_type: EntityType):
        entity_map = {
            EntityType.Devices: ("Devicedisabelable", "devices/disable"),
            EntityType.Users: ("Userdisabelable", "users/disable")
        }
        if entity_type not in entity_map:
            raise Exception("Weird entity type given")

        featurename, urlpath = entity_map[entity_type]

        entitys_uuids = self.get_request_data_as_object()
        if not entitys_uuids:
            return return_error("No entity uuids provided")
        entity_disabelables_adapters, entity_ids_by_adapters = \
            self._find_entities_by_uuid_for_adapter_with_feature(entitys_uuids, featurename, entity_type)

        err = ""
        for adapter_unique_name in entity_disabelables_adapters:
            entitys_by_adapter = entity_ids_by_adapters.get(adapter_unique_name)
            if entitys_by_adapter:
                response = self.request_remote_plugin(urlpath, adapter_unique_name, method='POST',
                                                      json=entitys_by_adapter)
                if response.status_code != 200:
                    logger.error(f"Error on disabling on {adapter_unique_name}: {response.content}")
                    err += f"Error on disabling on {adapter_unique_name}: {response.content}\n"

        return return_error(err, 500) if err else ("", 200)

    def _find_entities_by_uuid_for_adapter_with_feature(self, entity_uuids, feature, entity_type: EntityType):
        """
        Find all entity from adapters that have a given feature, from a given set of entities
        :return: plugin_unique_names of entity with given features, dict of plugin_unique_name -> id of adapter entity
        """
        with self._get_db_connection(False) as db_connection:
            entities = list(self._entity_db_map.get(entity_type).find(
                {'internal_axon_id': {
                    "$in": entity_uuids
                }}))

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
                                                               "$in": list(entities_ids_by_adapters.keys())
                                                           }
                                                       },
                                                       projection={
                                                           PLUGIN_UNIQUE_NAME: 1
                                                       }
                    )]
        return entitydisabelables_adapters, entities_ids_by_adapters

    def _entity_views(self, method, module_name):
        """
        Save or fetch views over the entities db
        :return:
        """
        entity_views_collection = self._get_collection(f'{module_name}_views', limited_user=False)
        if method == 'GET':
            mongo_filter = filter_archived()
            return jsonify(beautify_db_entry(entry) for entry in entity_views_collection.find(mongo_filter))

        # Handle POST request
        view_data = self.get_request_data_as_object()
        if not view_data.get('name'):
            return return_error(f'Name is required in order to save a view', 400)
        if not view_data.get('view'):
            return return_error(f'View data is required in order to save one', 400)
        update_result = entity_views_collection.replace_one({'name': view_data['name']}, view_data, upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error(f'View named {view_data.name} was not saved', 400)
        return ''

    def _entity_labels(self, db, namespace):
        """
        GET Find all tags that currently belong to devices, to form a set of current tag values
        POST Add new tags to the list of given devices
        DELETE Remove old tags from the list of given devices
        :return:
        """
        all_labels = set()
        with self._get_db_connection(False) as db_connection:
            if request.method == 'GET':
                for current_device in db.find({'$or': [{'labels': {'$exists': False}}, {'labels': {'$ne': []}}]},
                                              projection={'labels': 1}):
                    all_labels.update(current_device['labels'])
                return jsonify(all_labels)

            # Now handling POST and DELETE - they determine if the label is an added or removed one
            entities_and_labels = self.get_request_data_as_object()
            if not entities_and_labels.get('entities'):
                return return_error("Cannot label entities without list of entities.", 400)
            if not entities_and_labels.get('labels'):
                return return_error("Cannot label entities without list of labels.", 400)

            entities = [db.find_one({'internal_axon_id': entity_id})['specific_data'][0]
                        for entity_id in entities_and_labels['entities']]
            entities = [(entity[plugin_consts.PLUGIN_UNIQUE_NAME], entity['data']['id']) for entity in entities]

            response = namespace.add_many_labels(entities, labels=entities_and_labels['labels'],
                                                 are_enabled=request.method == 'POST')

            if response.status_code != 200:
                logger.error(f"Tagging did not complete. First {response.json()}")
                return_error(f'Tagging did not complete. First error: {response.json()}', 400)

            return '', 200

    ##########
    # DEVICE #
    ##########

    @paginated()
    @filtered()
    @sorted()
    @projectioned()
    @add_rule_unauthenticated("device")
    def get_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return jsonify(self._get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection, 'device'))

    @filtered()
    @sorted()
    @projectioned()
    @add_rule_unauthenticated("device/csv")
    def get_devices_csv(self, mongo_filter, mongo_sort, mongo_projection):
        return self._get_csv(mongo_filter, mongo_sort, mongo_projection, 'device')

    @add_rule_unauthenticated("device/<device_id>", methods=['GET'])
    def device_by_id(self, device_id):
        return self._entity_by_id('device', device_id, ['installed_software', 'security_patches', 'users'])

    @paginated()
    @filtered()
    @add_rule_unauthenticated("device/queries", methods=['POST', 'GET'])
    def device_queries(self, limit, skip, mongo_filter):
        return self._entity_queries(limit, skip, mongo_filter, 'device')

    @add_rule_unauthenticated("device/queries/<query_id>", methods=['DELETE'])
    def device_queries_delete(self, query_id):
        return self._entity_queries_delete('device', query_id)

    @filtered()
    @add_rule_unauthenticated("device/count")
    def get_devices_count(self, mongo_filter):
        return self._get_entities_count(mongo_filter, 'device')

    @add_rule_unauthenticated("device/fields")
    def device_fields(self):
        return jsonify(self._entity_fields('device'))

    @add_rule_unauthenticated("device/views", methods=['GET', 'POST'])
    def device_views(self):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self._entity_views(request.method, 'device')

    @add_rule_unauthenticated("device/labels", methods=['GET', 'POST', 'DELETE'])
    def device_labels(self):
        return self._entity_labels(self.devices_db_view, self.devices)

    @add_rule_unauthenticated("device/disable", methods=['POST'])
    def disable_device(self):
        return self._disable_entity(EntityType.Devices)

    #########
    # USER #
    #########

    @paginated()
    @filtered()
    @sorted()
    @projectioned()
    @add_rule_unauthenticated("user")
    def get_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return jsonify(self._get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection, 'user'))

    @filtered()
    @sorted()
    @projectioned()
    @add_rule_unauthenticated("user/csv")
    def get_users_csv(self, mongo_filter, mongo_sort, mongo_projection):
        return self._get_csv(mongo_filter, mongo_sort, mongo_projection, 'user')

    @add_rule_unauthenticated("user/<user_id>", methods=['GET'])
    def user_by_id(self, user_id):
        return self._entity_by_id('user', user_id, ['associated_devices'])

    @paginated()
    @filtered()
    @add_rule_unauthenticated("user/queries", methods=['POST', 'GET'])
    def user_queries(self, limit, skip, mongo_filter):
        return self._entity_queries(limit, skip, mongo_filter, 'user')

    @add_rule_unauthenticated("user/queries/<query_id>", methods=['DELETE'])
    def user_queries_delete(self, query_id):
        return self._entity_queries_delete('user', query_id)

    @filtered()
    @add_rule_unauthenticated("user/count")
    def get_users_count(self, mongo_filter):
        return self._get_entities_count(mongo_filter, 'user')

    @add_rule_unauthenticated("user/fields")
    def user_fields(self):
        return jsonify(self._entity_fields('user'))

    @add_rule_unauthenticated("user/disable", methods=['POST'])
    def disable_user(self):
        return self._disable_entity(EntityType.Users)

    @add_rule_unauthenticated("user/views", methods=['GET', 'POST'])
    def user_views(self):
        return self._entity_views(request.method, 'user')

    @add_rule_unauthenticated("user/labels", methods=['GET', 'POST', 'DELETE'])
    def user_labels(self):
        return self._entity_labels(self.users_db_view, self.users)

    ###########
    # ADAPTER #
    ###########

    def _get_plugin_schemas(self, db_connection, plugin_unique_name):
        """
        Get all schemas for a given plugin
        :param db: a db connection
        :param plugin_unique_name: the unique name of the plugin
        :return: dict
        """

        clients_value = db_connection[plugin_unique_name]['adapter_schema'].find_one(sort=[('adapter_version',
                                                                                            pymongo.DESCENDING)])
        if clients_value is None:
            return {}
        return {'clients': clients_value.get('schema')}

    @filtered()
    @add_rule_unauthenticated("adapters")
    def adapters(self, mongo_filter):
        """
        Get all adapters from the core
        :mongo_filter
        :return:
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        with self._get_db_connection(False) as db_connection:
            adapters_from_db = db_connection['core']['configs'].find({'$or': [{'plugin_type': 'Adapter'},
                                                                              {'plugin_type': 'ScannerAdapter'}]}).sort(
                [(plugin_consts.PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            adapters_to_return = []
            for adapter in adapters_from_db:
                if not adapter[plugin_consts.PLUGIN_UNIQUE_NAME] in plugins_available:
                    # Plugin not registered - unwanted in UI
                    continue

                clients_configured = db_connection[adapter[plugin_consts.PLUGIN_UNIQUE_NAME]]['clients'].find(
                    projection={'_id': 1}).count()
                status = ''
                if clients_configured:
                    clients_connected = db_connection[adapter[plugin_consts.PLUGIN_UNIQUE_NAME]]['clients'].find(
                        {'status': 'success'}, projection={'_id': 1}).count()
                    status = 'success' if clients_configured == clients_connected else 'warning'

                adapters_to_return.append({'plugin_name': adapter['plugin_name'],
                                           'unique_plugin_name': adapter[plugin_consts.PLUGIN_UNIQUE_NAME],
                                           'status': status,
                                           'supported_features': adapter['supported_features']
                                           })

            return jsonify(adapters_to_return)

    def _query_client_for_devices(self, request, adapter_unique_name):
        client_to_add = request.get_json(silent=True)
        if client_to_add is None:
            return return_error("Invalid client", 400)

        # adding client to specific adapter
        response = self.request_remote_plugin("clients", adapter_unique_name, method='put', json=client_to_add)
        if response.status_code != 200:
            # failed, return immediately
            return response.text, response.status_code

        # if there's no aggregator, that's fine
        try:
            self.request_remote_plugin(f"trigger/{adapter_unique_name}",
                                       plugin_consts.AGGREGATOR_PLUGIN_NAME, method='post')
            research_state = self.request_remote_plugin(f"state",
                                                        plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, method='get').json()
            if research_state[StateLevels.Phase.name] == Phases.Stable.name:
                logger.info('System is stable, triggering static correlator')
                self.request_remote_plugin(
                    f"trigger/execute", plugin_consts.STATIC_CORRELATOR_PLUGIN_NAME, method='post')
            else:
                logger.info('System is in research phase, not triggering static correlator')
        except Exception:
            # if there's no aggregator, there's nothing we can do
            pass
        return response.text, response.status_code

    @paginated()
    @add_rule_unauthenticated("adapters/<adapter_unique_name>/clients", methods=['PUT', 'GET'])
    def adapters_clients(self, adapter_unique_name, limit, skip):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param limit: for pagination (only for GET)
        :param skip: for pagination (only for GET)
        :return:
        """
        with self._get_db_connection(False) as db_connection:
            if request.method == 'GET':
                client_collection = db_connection[adapter_unique_name]['clients']
                return jsonify({
                    'schema': self._get_plugin_schemas(db_connection, adapter_unique_name)['clients'],
                    'clients': [beautify_db_entry(client) for client in
                                client_collection.find().skip(skip).limit(limit)]
                })
            if request.method == 'PUT':
                return self._query_client_for_devices(request, adapter_unique_name)

    @add_rule_unauthenticated("adapters/<adapter_unique_name>/clients/<client_id>", methods=['PUT', 'DELETE'])
    def adapters_clients_update(self, adapter_unique_name, client_id):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param client_id: UUID of client to delete
        :return:
        """
        self.request_remote_plugin("clients/" + client_id, adapter_unique_name, method='delete')
        if request.method == 'PUT':
            return self._query_client_for_devices(request, adapter_unique_name)
        if request.method == 'DELETE':
            return '', 200

    @add_rule_unauthenticated("actions/run_shell", methods=['POST'])
    def actions_run_shell(self):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """
        device_control_service_unique_name = self.get_plugin_by_name("device_control")
        data = self.get_request_data_as_object()

        # The format of data is defined in device_control\service.py::run_shell
        response = self.request_remote_plugin('run_shell', device_control_service_unique_name, 'post',
                                              data=data)
        if response.status_code != 200:
            self.logger.error(f"Couldn't execute run shell. Reason: {response.status_code}, {str(response.content)}")
            raise ValueError(f"Couldn't execute run shell. Reason: {response.status_code}, {str(response.content)}")

    @add_rule_unauthenticated("reports", methods=['GET', 'PUT'])
    def reports(self):
        """
        GET results in list of all currently configured alerts, with their query id they were created with
        PUT Send report_service a new report to be configured

        :return:
        """
        queries_collection = self._get_collection('device_queries', limited_user=False)
        if request.method == 'GET':
            with self._get_db_connection(False) as db_connection:
                reports_to_return = []
                report_service = self.get_plugin_by_name('reports')
                for report in db_connection[report_service[plugin_consts.PLUGIN_UNIQUE_NAME]]['reports'].find(
                        projection={
                            'name': 1, 'report_creation_time': 1, 'severity': 1, 'actions': 1, 'triggers': 1,
                            'retrigger': 1
                        }).sort([('report_creation_time', pymongo.DESCENDING)]):
                    # Fetching query in order to replace the string saved for aler
                    #  with the corresponding id that the UI can recognize the query as
                    query = queries_collection.find_one({'alertIds': {'$in': [str(report['_id'])]}})
                    if query is None:
                        continue
                    report['query'] = str(query['_id'])
                    reports_to_return.append(beautify_db_entry(report))
                return jsonify(reports_to_return)

        if request.method == 'PUT':
            report_to_add = request.get_json(silent=True)
            match_query = {'_id': ObjectId(report_to_add['query'])}
            query = queries_collection.find_one(match_query)
            if query is None or not query.get('filter'):
                return return_error("Invalid query id {0} requested for creating report".format(report_to_add['query']))

            logger.info("About to generate a report for the filter: {0}".format(query['filter']))
            report_to_add['query'] = query['filter']
            response = self.request_remote_plugin("reports", "reports", method='put', json=report_to_add)
            if response is not None and response.status_code == 201:
                # Updating saved query with the created report's id, for reference when fetching alerts
                report_ids = set(query.get('alertIds') or [])
                report_ids.add(response.text)
                queries_collection.update_one(match_query, {'$set': {'alertIds': list(report_ids)}})
            return response.text, response.status_code

    @add_rule_unauthenticated("reports/<report_id>", methods=['DELETE', 'POST'])
    def alerts_update(self, report_id):
        """

        :param alert_id:
        :return:
        """
        queries_collection = self._get_collection('device_queries', limited_user=False)
        if request.method == 'DELETE':
            response = self.request_remote_plugin("reports/{0}".format(report_id), "reports", method='delete')
            if response is None:
                return return_error("No response whether alert was removed")
            if response.status_code == 200:
                query = queries_collection.find_one({'alertIds': {'$in': [report_id]}})
                if query is not None:
                    report_ids = set(query.get('alertIds') or [])
                    report_ids.remove(report_id)
                    queries_collection.update_one({'_id': query['_id']}, {'$set': {'alertIds': list(report_ids)}})
                    logger.info("Removed alert from containing query {0}".format(query['_id']))
            return response.text, response.status_code

        if request.method == 'POST':
            report_to_update = request.get_json(silent=True)
            match_query = {'_id': ObjectId(report_to_update['query'])}
            query = queries_collection.find_one(match_query)
            if query is None or not query.get('filter'):
                return return_error(
                    "Invalid query id {0} requested for creating alert".format(report_to_update['query']))

            report_to_update['query'] = query['filter']
            response = self.request_remote_plugin("reports/{0}".format(report_id), "reports", method='post',
                                                  json=report_to_update)
            if response is None:
                return return_error("No response whether alert was updated")

            if response.status_code == 200:
                # Remove alert from any queries holding it now
                query = queries_collection.find_one({'alertIds': {'$in': [report_id]}})
                if query is not None:
                    report_ids = set(query.get('alertIds') or [])
                    report_ids.remove(report_id)
                    queries_collection.update_one({'_id': query['_id']}, {'$set': {'alertIds': list(report_ids)}})
                # Updating saved query with the created alert's id, for reference when fetching alerts
                report_ids = set(query.get('alertIds') or [])
                report_ids.add(response.text)
                queries_collection.update_one(match_query, {'$set': {'alertIds': list(report_ids)}})

            return response.text, response.status_code

    @filtered()
    @add_rule_unauthenticated("plugins")
    def plugins(self, mongo_filter):
        """
        Get all plugins configured in core and update each one's status.
        Status will be "error" if the plugin is not registered.
        Otherwise it will be "success", if currently running or "warning", if  stopped.

        :mongo_filter
        :return: List of plugins with
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        with self._get_db_connection(False) as db_connection:
            plugins_from_db = db_connection['core']['configs'].find({'plugin_type': 'Plugin'}).sort(
                [(plugin_consts.PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            plugins_to_return = []
            for plugin in plugins_from_db:
                # TODO check supported features
                if plugin['plugin_type'] != "Plugin" or plugin['plugin_name'] in [plugin_consts.AGGREGATOR_PLUGIN_NAME,
                                                                                  "gui",
                                                                                  "watch_service",
                                                                                  "execution",
                                                                                  "system_scheduler"]:
                    continue

                processed_plugin = {'plugin_name': plugin['plugin_name'],
                                    'unique_plugin_name': plugin[plugin_consts.PLUGIN_UNIQUE_NAME],
                                    'status': 'error',
                                    'state': 'Disabled'
                                    }
                if plugin[plugin_consts.PLUGIN_UNIQUE_NAME] in plugins_available:
                    processed_plugin['status'] = 'warning'
                    response = self.request_remote_plugin(
                        "trigger_state/execute", plugin[plugin_consts.PLUGIN_UNIQUE_NAME])
                    if response.status_code != 200:
                        logger.error("Error getting state of plugin {0}".format(
                            plugin[plugin_consts.PLUGIN_UNIQUE_NAME]))
                        processed_plugin['status'] = 'error'
                    else:
                        processed_plugin['state'] = response.json()
                        if (processed_plugin['state']['state'] != 'Disabled'):
                            processed_plugin['status'] = "success"
                plugins_to_return.append(processed_plugin)

            return jsonify(plugins_to_return)

    @add_rule_unauthenticated("plugins/<plugin_unique_name>/<command>", methods=['POST'])
    def run_plugin(self, plugin_unique_name, command):
        """
        Calls endpoint of given plugin_unique_name, according to given command
        The command should comply with the /supported_features of the plugin

        :param plugin_unique_name:
        :return:
        """
        request_data = self.get_request_data_as_object()
        response = self.request_remote_plugin(f"{command}/{request_data['trigger']}", plugin_unique_name, method='post')
        if response and response.status_code == 200:
            return ""
        return response.json(), response.status_code

    @add_rule_unauthenticated("config/<config_name>", methods=['POST', 'GET'])
    def config(self, config_name):
        """
        Get or set config by name
        :param config_name: Config to fetch
        :return:
        """
        configs_collection = self._get_collection('config', limited_user=False)
        if request.method == 'GET':
            return jsonify(
                configs_collection.find_one({'name': config_name},
                                            )['value'])
        if request.method == 'POST':
            config_to_add = request.get_json(silent=True)
            if config_to_add is None:
                return return_error("Invalid filter", 400)
            configs_collection.update({'name': config_name},
                                      {'name': config_name, 'value': config_to_add},
                                      upsert=True)
            return ""

    @paginated()
    @filtered()
    @add_rule_unauthenticated("notifications", methods=['POST', 'GET'])
    def notifications(self, limit, skip, mongo_filter):
        """
        Get all notifications
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        with self._get_db_connection(False) as db:
            notification_collection = db['core']['notifications']
            if request.method == 'GET':
                return jsonify(beautify_db_entry(n) for n in
                               notification_collection.find(mongo_filter, projection={
                                   "_id": 1,
                                   "who": 1,
                                   "plugin_name": 1,
                                   "type": 1,
                                   "title": 1,
                                   "seen": 1,
                                   "severity": 1}).skip(skip).limit(limit))
            elif request.method == 'POST':
                notifications_to_see = request.get_json(silent=True)
                if notifications_to_see is None:
                    return return_error("Invalid notification list", 400)
                update_result = notification_collection.update_many(
                    {"_id": {"$in": [ObjectId(x) for x in notifications_to_see.get('notification_ids', [])]}
                     }, {"$set": {'seen': notifications_to_see.get('seen', True)}})
                return str(update_result.modified_count), 200

    @filtered()
    @add_rule_unauthenticated("notifications/count", methods=['GET'])
    def notifications_count(self, mongo_filter):
        """
        Fetches from core's notification collection, according to given mongo_filter,
        and counts how many entries in retrieved cursor
        :param mongo_filter: Generated by the filtered() decorator, according to uri param "filter"
        :return: Number of notifications matching given filter
        """
        with self._get_db_connection(False) as db:
            notification_collection = db['core']['notifications']
            return str(notification_collection.find(mongo_filter).count())

    @add_rule_unauthenticated("notifications/<notification_id>", methods=['GET'])
    def notifications_by_id(self, notification_id):
        """
        Get all notification data
        :param notification_id: Notification ID
        :return:
        """
        with self._get_db_connection(False) as db:
            notification_collection = db['core']['notifications']
            return jsonify(beautify_db_entry(notification_collection.find_one({'_id': ObjectId(notification_id)})))

    @add_rule("login", methods=['GET', 'POST'], should_authenticate=False)
    def login(self):
        """
        Get current user or login
        :return:
        """
        if request.method == 'GET':
            user = session.get('user')
            if user is None:
                return return_error("Enter credentials to log in", 401)
            del user['password']
            return jsonify(user), 200

        users_collection = self._get_collection('users', limited_user=False)
        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error("No login data provided", 400)
        user_name = log_in_data.get('user_name')
        password = log_in_data.get('password')
        user_from_db = users_collection.find_one({'user_name': user_name})
        if user_from_db is None:
            logger.info(f"Unknown user {user_name} tried logging in")
            return return_error("Wrong user name or password", 401)
        if not bcrypt.verify(password, user_from_db['password']):
            logger.info(f"User {user_name} tried logging in with wrong password")
            return return_error("Wrong user name or password", 401)
        session['user'] = user_from_db
        return ""

    @add_rule_unauthenticated("logout", methods=['GET'])
    def logout(self):
        """
        Clears session, logs out
        :return:
        """
        session['user'] = None
        return ""

    # @paginated()
    # @add_rule("users", methods=['GET', 'POST'])
    # def users(self, limit, skip):
    #     """
    #     View or add users
    #     :param limit: limit for pagination
    #     :param skip: start index for pagination
    #     :return:
    #     """
    #     users_collection = self._get_collection('users', limited_user=False)
    #     if request.method == 'GET':
    #         return jsonify(beautify_db_entry(n) for n in
    #                        users_collection.find(projection={
    #                            "_id": 1,
    #                            "user_name": 1,
    #                            "first_name": 1,
    #                            "last_name": 1,
    #                            "pic_name": 1}).sort(
    #                            [('_id', pymongo.ASCENDING)]).skip(skip).limit(limit))
    #     elif request.method == 'POST':
    #         user_data = self.get_request_data_as_object()
    #         users_collection.update({'user_name': user_data['user_name']},
    #                                 {'user_name': user_data['user_name'],
    #                                  'first_name': user_data.get('first_name'),
    #                                  'last_name': user_data.get('last_name'),
    #                                  'pic_name': user_data.get('pic_name'),
    #                                  'password': bcrypt.hash(user_data['password']),
    #                                  },
    #                                 upsert=True)
    #         return "", 201

    @paginated()
    @add_rule_unauthenticated("logs")
    def logs(self, limit, skip):
        """
        Maybe this should be datewise paginated, perhaps the whole scheme will change.
        :param limit: pagination
        :param skip:
        :return:
        """
        es = Elasticsearch(hosts=[self._elk_addr], http_auth=self._elk_auth)
        res = es.search(index='logstash-*', doc_type='logstash-log',
                        body={'size': limit,
                              'from': skip,
                              'sort': [{'@timestamp': {'order': 'desc'}}]})
        return jsonify(res['hits']['hits'])

    @gzipped_downloadable("axonius_logs_{}", "json")
    @add_rule("logs/export", should_authenticate=False)
    def logs_export(self):
        """
        Pass 'start_date' and/or 'end_date' in GET parameters
        :return:
        """
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        es = Elasticsearch(hosts=[self._elk_addr], http_auth=self._elk_auth)
        res = es.search(index='logstash-*', doc_type='logstash-log',
                        body={
                            "query": {
                                "range": {  # expect this to return the one result on 2012-12-20
                                    "@timestamp": {
                                        "gte": start_date,
                                        "lte": end_date,
                                    }
                                }
                            }
                        })
        return json.dumps(list(res['hits']['hits']))

    #############
    # DASHBOARD #
    #############

    @add_rule_unauthenticated("dashboard", methods=['POST', 'GET'])
    def get_dashboard(self):
        """
        GET Fetch current dashboard chart definitions. For each definition, fetch each of it's queries and
        fetch devices_db_view with their view. Amount of results is mapped to each queries' name, under 'data' key,
        to be returned with the dashboard definition.

        POST Save a new dashboard chart definition, given it has a name and at least one query attached

        :return:
        """
        dashboard_collection = self._get_collection('dashboard', limited_user=False)
        if request.method == 'GET':
            dashboard_list = []
            for dashboard_object in dashboard_collection.find(filter_archived()):
                if not dashboard_object.get('name'):
                    logger.info(f'No name for dashboard {dashboard_object["_id"]}')
                elif not dashboard_object.get('queries'):
                    logger.info(f'No queries found for dashboard {dashboard_object.get("name")}')
                else:
                    # Let's fetch and run them query filters
                    for module_name in dashboard_object['queries']:
                        queries_collection = self._get_collection(f'{module_name}_queries', limited_user=False)
                        for query_name in dashboard_object['queries'][module_name]:
                            query_object = queries_collection.find_one({'name': query_name})
                            if not query_object or not query_object.get('filter'):
                                logger.info(f'No filter found for query {query_name}')
                            else:
                                if not dashboard_object.get('data'):
                                    dashboard_object['data'] = {}
                                dashboard_object['data'][query_name] = self.aggregator_db_connection[
                                    f'{module_name}s_db_view'].find(parse_filter(query_object['filter']), {'_id': 1}).count()

                    dashboard_list.append(beautify_db_entry(dashboard_object))
            return jsonify(dashboard_list)

        # Handle 'POST' request method - save dashboard configuration
        dashboard_object = self.get_request_data_as_object()
        if not dashboard_object.get('name'):
            return return_error('Name required in order to save Dashboard Chart', 400)
        if not dashboard_object.get('queries'):
            return return_error('At least one query required in order to save Dashboard Chart', 400)
        update_result = dashboard_collection.replace_one({'name': dashboard_object['name']}, dashboard_object,
                                                         upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error('Error saving dashboard chart', 400)
        return ''

    @add_rule_unauthenticated("dashboard/<dashboard_id>", methods=['DELETE'])
    def remove_dashboard(self, dashboard_id):
        """
        Fetches data, according to definition saved for the dashboard named by given name

        :param dashboard_name: Name of the dashboard to fetch data for
        :return:
        """
        update_result = self._get_collection('dashboard', limited_user=False).replace_one(
            {'_id': ObjectId(dashboard_id)}, {'archived': True})
        if not update_result.modified_count:
            return return_error(f'No dashboard by the id {dashboard_id} found or updated', 400)
        return ''

    @add_rule_unauthenticated("dashboard/lifecycle", methods=['GET'])
    def get_system_lifecycle(self):
        """
        Fetches and build data needed for presenting current status of the system's lifecycle in a graph

        :return: Data containing:
         - All research phases names, for showing the whole picture
         - Current research sub-phase, which is empty if system is not stable
         - Portion of work remaining for the current sub-phase
         - The time next cycle is scheduled to run
        """
        state_response = self.request_remote_plugin('state', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME)
        if state_response.status_code != 200:
            return return_error(f"Error fetching status of system scheduler. Reason: {state_response.text}")

        state = state_response.json()
        is_research = state[StateLevels.Phase.name] == Phases.Research.name

        # Map each sub-phase to a dict containing its name and status, which is determined by:
        # - Sub-phase prior to current sub-phase - 1
        # - Current sub-phase - complementary of retrieved status (indicating complete portion)
        # - Sub-phase subsequent to current sub-phase - 0
        sub_phases = []
        found_current = False
        for sub_phase in ResearchPhases:
            if is_research and sub_phase.name == state[StateLevels.SubPhase.name]:
                # Reached current status - set complementary of SubPhaseStatus value
                found_current = True
                sub_phases.append({'name': sub_phase.name, 'status': 1 - (state[StateLevels.SubPhaseStatus.name] or 1)})
            else:
                # Set 0 or 1, depending if reached current status yet
                sub_phases.append({'name': sub_phase.name, 'status': 0 if found_current else 1})

        run_time_response = self.request_remote_plugin('next_run_time', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME)
        if run_time_response.status_code != 200:
            return return_error(f"Error fetching run time of system scheduler. Reason: {run_time_response.text}")

        return jsonify({'sub_phases': sub_phases, 'next_run_time': run_time_response.text})

    @add_rule_unauthenticated("dashboard/lifecycle_rate", methods=['GET', 'POST'])
    def system_lifecycle_rate(self):
        """

        """
        if self.get_method() == 'GET':
            response = self.request_remote_plugin('research_rate', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME)
            return response.content
        elif self.get_method() == 'POST':
            response = self.request_remote_plugin(
                'research_rate', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, method='POST',
                json=self.get_request_data_as_object())
            logger.info(f"response code: {response.status_code} response crap: {response.content}")
            return ''

    @add_rule_unauthenticated("dashboard/adapter_devices", methods=['GET'])
    def get_adapter_devices(self):
        """
        For each adapter currently registered in system, count how many devices it fetched.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        adapter_devices = {'total_gross': 0, 'adapter_count': {}}
        with self._get_db_connection(False) as db_connection:
            adapter_devices['total_net'] = db_connection[plugin_consts.AGGREGATOR_PLUGIN_NAME]['devices_db'].find({
            }).count()
            adapters_from_db = db_connection['core']['configs'].find({'plugin_type': 'Adapter'})
            for adapter in adapters_from_db:
                if not adapter[plugin_consts.PLUGIN_UNIQUE_NAME] in plugins_available:
                    # Plugin not registered - unwanted in UI
                    continue
                devices_count = db_connection[plugin_consts.AGGREGATOR_PLUGIN_NAME]['devices_db'].find(
                    {'adapters.plugin_name': adapter['plugin_name']}).count()
                if not devices_count:
                    # No need to document since adapter has no devices
                    continue
                adapter_devices['adapter_count'][adapter['plugin_name']] = devices_count
                adapter_devices['total_gross'] = adapter_devices['total_gross'] + devices_count

        return jsonify(adapter_devices)

    @add_rule_unauthenticated("dashboard/coverage", methods=['GET'])
    def get_dashboard_coverage(self):
        """
        Measures the coverage portion, according to sets of properties that devices' adapters may have.
        Portion is calculated out of total devices amount.
        Currently returns coverage for devices composed of adapters that are:
        - Managed ('Manager' or 'Agent')
        - Endpoint Protected
        - Vulnerability Assessed

        :return:
        """
        coverage_list = [
            {'title': 'Managed Device', 'properties': [AdapterProperty.Manager.name, AdapterProperty.Agent.name],
             'description': 'Deploy appropriate agents on unmanaged devices, and add them to Active Directory.'},
            {'title': 'Endpoint Protection', 'properties': [AdapterProperty.Endpoint_Protection_Platform.name],
             'description': 'Add an endpoint protection solution to uncovered devices.'},
            {'title': 'VA Scanner', 'properties': [AdapterProperty.Vulnerability_Assessment.name],
             'description': 'Add uncovered devices to the next scheduled vulnerability assessment scan.'}
        ]
        for item in coverage_list:
            devices_property = self.aggregator_db_connection['devices_db_view'].find(
                {'specific_data.adapter_properties': {'$in': item['properties']}}).count()
            devices_total = self.aggregator_db_connection['devices_db_view'].find({}).count()
            item['portion'] = devices_property / devices_total
        return jsonify(coverage_list)

    @add_rule_unauthenticated("research_phase", methods=['POST'])
    def schedule_research_phase(self):
        """
        Schedules or initiates research phase.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        data = self.get_request_data_as_object()
        logger.info(f"Scheduling Research Phase to: {data if data else 'Now'}")
        response = self.request_remote_plugin(
            'trigger/execute', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json=data)

        if response.status_code != 200:
            logger.error(f"Could not schedule research phase to: {data if data else 'Now'}")
            return return_error(f"Could not schedule research phase to: {data if data else 'Now'}",
                                response.status_code)

        return ''

    #############
    # SETTINGS #
    #############

    @add_rule_unauthenticated("settings", methods=['POST', 'GET'])
    def settings(self):
        """
        Gets or saves current settings for the system

        :return:
        """
        settings_collection = self._get_collection('settings', limited_user=False)
        if (request.method == 'GET'):
            settings_object = settings_collection.find_one({})
            if not settings_object:
                return jsonify({})
            return jsonify(beautify_db_entry(settings_object))

        # Handle POST request
        settings_object = self.get_request_data_as_object()
        update_result = settings_collection.replace_one({}, settings_object, upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error('Error saving settings', 400)
        return ''

    @add_rule_unauthenticated("email_server", methods=['POST', 'GET', 'DELETE'])
    def email_server(self):
        """
        Adds, Gets and Deletes currently saved mail servers

        :return: Map between each adapter and the number of devices it has, unless no devices
        """

        response = self.request_remote_plugin('email_server', None, self.get_method(),
                                              json=self.get_request_data_as_object())
        if self.get_method() in ('POST', 'GET') and response.status_code == 200:
            return jsonify(response.json())
        else:
            return response.content, response.status_code

    @add_rule_unauthenticated("execution/<plugin_state>", methods=['POST'])
    def toggle_execution(self, plugin_state):
        services = ['execution', 'careful_execution_correlator', 'general_info']
        statuses = []
        for current_service in services:
            response = self.request_remote_plugin('plugin_state', current_service, 'POST',
                                                  params={'wanted': plugin_state})

            if response.status_code != 200:
                logger.error(f"Failed to {plugin_state} {current_service}.")
                statuses.append(False)
            else:
                logger.info(f"Switched {current_service} to be {plugin_state}.")
                statuses.append(True)

        return '' if all(statuses) else return_error(f'Failed to {plugin_state} all plugins', 500)

    @add_rule_unauthenticated("execution", methods=['GET'])
    def get_execution(self):
        services = ['execution', 'careful_execution_correlator', 'general_info']
        enabled = False
        for current_service in services:
            response = self.request_remote_plugin('plugin_state', current_service)
            if response.status_code == 200 and response.json()['state'] == 'enabled':
                enabled = True
                break

        return 'enabled' if enabled else 'disabled'

    @property
    def plugin_subtype(self):
        return "Core"
