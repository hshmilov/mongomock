from axonius.utils.files import get_local_config_file
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.devices.device import Device
from axonius.users.user import User
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, PLUGIN_NAME, AGGREGATOR_PLUGIN_NAME, \
    SYSTEM_SCHEDULER_PLUGIN_NAME
from axonius.consts.scheduler_consts import ResearchPhases, StateLevels, Phases

import tarfile
import io
import os
from datetime import date
from flask import jsonify, request, session, after_this_request
from passlib.hash import bcrypt
from elasticsearch import Elasticsearch
import requests
import configparser
import pymongo
from bson import ObjectId
import json
from datetime import datetime
from axonius.parsing_utils import parse_filter

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
    Decorator stating that the view supports ?filter='adapters == "ad_adapter"'
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            filter_obj = dict()
            try:
                filter_expr = request.args.get('filter')
                if filter_expr:
                    self.logger.info("Parsing filter: {0}".format(filter_expr))
                    filter_obj = parse_filter(filter_expr)
                    self.logger.info("Got filter: {0}".format(filter_obj))
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
                    self.logger.debug(f'Parsing sort: {sort_param}')
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
    return {'$or': [{}, {'archived': {'$exists': False}}, {'archived': False}]}


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
        self.add_default_device_queries()

    def add_default_device_queries(self):
        # Load default queries and save them to the DB
        try:
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), 'default_queries.ini')))

            # Save default queries
            for name, query in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    self._insert_query('device', name, query['query'])
                except:
                    self.logger.exception(f'Error adding default query {name}')
        except:
            self.logger.exception(f'Error adding default queries')

    def _insert_query(self, module_name, name, query_filter, query_expressions=[]):
        queries_collection = self._get_collection(f'{module_name}_queries', limited_user=False)
        existed_query = queries_collection.find_one({'filter': query_filter, 'name': name})
        if existed_query is not None:
            self.logger.info(f'Query {name} already exists id: {existed_query["_id"]}')
            return existed_query['_id']
        result = queries_collection.update({'name': name}, {'$set': {'name': name, 'filter': query_filter,
                                                                     'expressions': query_expressions,
                                                                     'query_type': 'saved', 'timestamp': datetime.now(),
                                                                     'archived': False}}, upsert=True)
        self.logger.info(f'Added query {name} id: {result.get("inserted_id", "")}')
        return result.get('inserted_id', '')

    ########
    # DATA #
    ########

    def _get_entities(self, limit, skip, filter, sort, projection, module_name):
        """
        Get Axonius data of type <module_name>, from the aggregator which is expected to store them.
        """
        self.logger.debug(f'Fetching data for module {module_name}')
        with self._get_db_connection(False) as db_connection:
            pipeline = [{'$match': filter}]
            if projection:
                projection['internal_axon_id'] = 1
                projection['adapters'] = 1
                pipeline.append({'$project': projection})
            if sort:
                self.logger.info(f'HERE IS SORT {sort}')
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
            data_list = db_connection[AGGREGATOR_PLUGIN_NAME][f'{module_name}s_db_view'].aggregate(
                pipeline, allowDiskUse=True)

            if filter and not skip:
                filter = request.args.get('filter')
                db_connection[self.plugin_unique_name][f'{module_name}_queries'].replace_one(
                    {'name': {'$exists': False}, 'filter': filter},
                    {'filter': filter, 'query_type': 'history', 'timestamp': datetime.now(), 'archived': False},
                    upsert=True)
            return jsonify(beautify_db_entry(entity) for entity in data_list)

    def _entity_by_id(self, module_name, entity_id):
        """
        Retrieve device by the given id, from current devices DB or update it
        Currently, update works only for tags because that is the only edit operation user has
        :return:
        """
        with self._get_db_connection(False) as db_connection:
            entity = db_connection[AGGREGATOR_PLUGIN_NAME][f'{module_name}s_db_view'].find_one(
                {'internal_axon_id': entity_id})
            if entity is None:
                return return_error("Entity ID wasn't found", 404)
            return jsonify(entity)

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
            if query_to_add is None:
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
            data_collection = db_connection[AGGREGATOR_PLUGIN_NAME][f'{module_name}s_db_view']
            return str(data_collection.find(filter, {'_id': 1}).count())

    def _entity_fields(self, module_name):
        """
        Get generic fields schema as well as adapter-specific parsed fields schema.
        Together these are all fields that any device may have data for and should be presented in UI accordingly.
        :return:
        """

        def _censor_fields(fields):
            # Remove fields from data that are not relevant to UI
            fields['items'] = filter(lambda x: x.get('name', '') not in ['scanner'], fields['items'])
            return fields

        fields = {'generic': _censor_fields(Device.get_fields_info()), 'specific': {}}
        with self._get_db_connection(False) as db_connection:
            plugins_from_db = db_connection['core']['configs'].find({}).sort(
                [(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            for plugin in plugins_from_db:
                if db_connection[plugin[PLUGIN_UNIQUE_NAME]]['fields']:
                    plugin_fields_record = db_connection[plugin[PLUGIN_UNIQUE_NAME]][f'{module_name}_fields'].find_one(
                        {'name': 'parsed'}, projection={'schema': 1})
                    if plugin_fields_record:
                        fields['specific'][plugin[PLUGIN_NAME]] = _censor_fields(plugin_fields_record['schema'])

        return jsonify(fields)

    ##########
    # DEVICE #
    ##########

    @paginated()
    @filtered()
    @sorted()
    @projectioned()
    @add_rule_unauthenticated("device")
    def get_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return self._get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection, 'device')

    @add_rule_unauthenticated("device/<device_id>", methods=['GET'])
    def _device_by_id(self, device_id):
        return self._entity_by_id('device', device_id)

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
        return self._entity_fields('device')

    @add_rule_unauthenticated("device/views", methods=['GET', 'POST'])
    def device_views(self):
        """
        Save or fetch views over the devices db
        :return:
        """
        device_views_collection = self._get_collection('device_views', limited_user=False)
        if request.method == 'GET':
            mongo_filter = filter_archived()
            return jsonify(beautify_db_entry(entry) for entry in device_views_collection.find(mongo_filter))

        # Handle POST request
        view_data = self.get_request_data_as_object()
        if not view_data.get('name'):
            return return_error(f'Name is required in order to save a view', 400)
        if not view_data.get('view'):
            return return_error(f'View data is required in order to save one', 400)
        update_result = device_views_collection.replace_one({'name': view_data['name']}, view_data, upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error(f'View named {view_data.name} was not saved', 400)
        return ''

    @add_rule_unauthenticated("device/labels", methods=['GET', 'POST', 'DELETE'])
    def labels(self):
        """
        GET Find all tags that currently belong to devices, to form a set of current tag values
        POST Add new tags to the list of given devices
        DELETE Remove old tags from the list of given devices
        :return:
        """
        all_labels = set()
        with self._get_db_connection(False) as db_connection:
            devices_collection = db_connection[AGGREGATOR_PLUGIN_NAME]['devices_db']
            if request.method == 'GET':
                for current_device in devices_collection.find({"tags.type": "label"}, projection={"tags": 1}):
                    for current_label in current_device['tags']:
                        if current_label['type'] == 'label' and current_label['data'] == True:
                            all_labels.add(current_label['name'])
                return jsonify(all_labels)

            # Now handling POST and DELETE - they determine if the label is an added or removed one
            devices_and_labels = self.get_request_data_as_object()
            if not devices_and_labels.get('devices'):
                return return_error("Cannot label devices without list of devices.", 400)
            if not devices_and_labels.get('labels'):
                return return_error("Cannot label devices without list of labels.", 400)

            devices = [devices_collection.find_one({'internal_axon_id': device_id})['adapters'][0]
                       for device_id in
                       devices_and_labels['devices']]
            devices = [(device[PLUGIN_UNIQUE_NAME], device['data']['id'])
                       for device in devices]

            response = self.devices.add_many_labels(devices,
                                                    labels=devices_and_labels['labels'],
                                                    are_enabled=request.method == 'POST')

            if response.status_code != 200:
                self.logger.error(f"Tagging did not complete. First {response.json()}")
                return_error(f'Tagging did not complete. First error: {response.json()}', 400)

            return '', 200

    #########
    # USER #
    #########

    @paginated()
    @filtered()
    @sorted()
    @projectioned()
    @add_rule_unauthenticated("user")
    def get_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return self._get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection, 'user')

    @add_rule_unauthenticated("user/<user_id>", methods=['GET'])
    def user_by_id(self, user_id):
        return self._entity_by_id('user', user_id)

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
        return self._entity_fields('user')

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
                [(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            adapters_to_return = []
            for adapter in adapters_from_db:
                if not adapter[PLUGIN_UNIQUE_NAME] in plugins_available:
                    # Plugin not registered - unwanted in UI
                    continue

                clients_configured = db_connection[adapter[PLUGIN_UNIQUE_NAME]]['clients'].find(
                    projection={'_id': 1}).count()
                status = ''
                if clients_configured:
                    clients_connected = db_connection[adapter[PLUGIN_UNIQUE_NAME]]['clients'].find(
                        {'status': 'success'}, projection={'_id': 1}).count()
                    status = 'success' if clients_configured == clients_connected else 'warning'

                adapters_to_return.append({'plugin_name': adapter['plugin_name'],
                                           'unique_plugin_name': adapter[PLUGIN_UNIQUE_NAME],
                                           'status': status
                                           })

            return jsonify(adapters_to_return)

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
                    self.request_remote_plugin(f"trigger/{adapter_unique_name}", AGGREGATOR_PLUGIN_NAME, method='post')
                except Exception:
                    # if there's no aggregator, there's nothing we can do
                    pass
                return response.text, response.status_code

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
            client_to_update = request.get_json(silent=True)
            response = self.request_remote_plugin("clients", adapter_unique_name, method='put', json=client_to_update)
            return response.text, response.status_code
        if request.method == 'DELETE':
            return '', 200

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
                for report in db_connection[report_service[PLUGIN_UNIQUE_NAME]][
                        'reports'].find().sort(
                        [('report_creation_time', pymongo.DESCENDING)]):
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

            self.logger.info("About to generate a report for the filter: {0}".format(query['filter']))
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
                    self.logger.info("Removed alert from containing query {0}".format(query['_id']))
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
                [(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            plugins_to_return = []
            for plugin in plugins_from_db:
                # TODO check supported features
                if plugin['plugin_type'] != "Plugin" or plugin['plugin_name'] in [AGGREGATOR_PLUGIN_NAME, "gui",
                                                                                  "watch_service",
                                                                                  "execution",
                                                                                  "system_scheduler"]:
                    continue

                processed_plugin = {'plugin_name': plugin['plugin_name'],
                                    'unique_plugin_name': plugin[PLUGIN_UNIQUE_NAME],
                                    'status': 'error',
                                    'state': 'Disabled'
                                    }
                if plugin[PLUGIN_UNIQUE_NAME] in plugins_available:
                    processed_plugin['status'] = 'warning'
                    response = self.request_remote_plugin("trigger_state/execute", plugin[PLUGIN_UNIQUE_NAME])
                    if response.status_code != 200:
                        self.logger.error("Error getting state of plugin {0}".format(plugin[PLUGIN_UNIQUE_NAME]))
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
            self.logger.info(f"Unknown user {user_name} tried logging in")
            return return_error("Wrong user name or password", 401)
        if not bcrypt.verify(password, user_from_db['password']):
            self.logger.info(f"User {user_name} tried logging in with wrong password")
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
        with self._get_db_connection(False) as db_connection:
            dashboard_collection = self._get_collection('dashboard', limited_user=False)
            queries_collection = self._get_collection('device_queries', limited_user=False)
            devices_collection = db_connection[AGGREGATOR_PLUGIN_NAME]['devices_db_view']
            if request.method == 'GET':
                dashboard_list = []
                for dashboard_object in dashboard_collection.find(filter_archived()):
                    if not dashboard_object.get('name'):
                        self.logger.info(f'No name for dashboard {dashboard_object["_id"]}')
                    elif not dashboard_object.get('queries'):
                        self.logger.info(f'No queries found for dashboard {dashboard_object.get("name")}')
                    else:
                        # Let's fetch and run them query filters
                        for query_name in dashboard_object['queries']:
                            query_object = queries_collection.find_one({'name': query_name})
                            if not query_object or not query_object.get('filter'):
                                self.logger.info(f'No filter found for query {query_name}')
                            else:
                                if not dashboard_object.get('data'):
                                    dashboard_object['data'] = {}
                                dashboard_object['data'][query_name] = devices_collection.find(
                                    parse_filter(query_object['filter']), {'_id': 1}).count()

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

    @add_rule_unauthenticated("dashboard/<dashboard_name>", methods=['GET'])
    def dashboard_chart(self, dashboard_name):
        """
        Fetches data, according to definition saved for the dashboard named by given name

        :param dashboard_name: Name of the dashboard to fetch data for
        :return:
        """
        dashboard_object = self._get_collection('dashboard', limited_user=False).find({'name': dashboard_name})
        if not dashboard_object:
            self.logger.info(f'No dashboard by the name {dashboard_name} found')
            return jsonify([])
        if not dashboard_object.get('queries'):
            self.logger.info(f'No queries found for dashboard {dashboard_name}')
            return jsonify([])

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
        state_response = self.request_remote_plugin('state', SYSTEM_SCHEDULER_PLUGIN_NAME)
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

        run_time_response = self.request_remote_plugin('next_run_time', SYSTEM_SCHEDULER_PLUGIN_NAME)
        if run_time_response.status_code != 200:
            return return_error(f"Error fetching run time of system scheduler. Reason: {run_time_response.text}")

        return jsonify({'sub_phases': sub_phases, 'next_run_time': run_time_response.text})

    @add_rule_unauthenticated("dashboard/lifecycle_rate", methods=['GET', 'POST'])
    def system_lifecycle_rate(self):
        """

        """
        if self.get_method() == 'GET':
            response = self.request_remote_plugin('research_rate', SYSTEM_SCHEDULER_PLUGIN_NAME)
            return response.content
        elif self.get_method() == 'POST':
            response = self.request_remote_plugin(
                'research_rate', SYSTEM_SCHEDULER_PLUGIN_NAME, method='POST', json=self.get_request_data_as_object())
            self.logger.info(f"response code: {response.status_code} response crap: {response.content}")
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
            adapters_from_db = db_connection['core']['configs'].find({'$or': [{'plugin_type': 'Adapter'},
                                                                              {'plugin_type': 'ScannerAdapter'}]})
            for adapter in adapters_from_db:
                if not adapter[PLUGIN_UNIQUE_NAME] in plugins_available:
                    # Plugin not registered - unwanted in UI
                    continue
                devices_count = db_connection[AGGREGATOR_PLUGIN_NAME]['devices_db'].find(
                    {'adapters.plugin_name': adapter['plugin_name']}).count()
                if not devices_count:
                    # No need to document since adapter has no devices
                    continue
                adapter_devices['adapter_count'][adapter['plugin_name']] = devices_count
                adapter_devices['total_gross'] = adapter_devices['total_gross'] + devices_count
            adapter_devices['total_net'] = db_connection[AGGREGATOR_PLUGIN_NAME]['devices_db'].find({}).count()

        return jsonify(adapter_devices)

    @add_rule_unauthenticated("research_phase", methods=['POST'])
    def schedule_research_phase(self):
        """
        Schedules or initiates research phase.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        data = self.get_request_data_as_object()
        self.logger.info(f"Scheduling Research Phase to: {data if data else 'Now'}")
        response = self.request_remote_plugin('trigger/execute', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json=data)

        if response.status_code != 200:
            self.logger.error(f"Could not schedule research phase to: {data if data else 'Now'}")
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
        services = ['execution', 'careful_execution_correlator_plugin', 'general-info-plugin']
        statuses = []
        for current_service in services:
            response = self.request_remote_plugin('plugin_state', current_service, 'POST',
                                                  params={'wanted': plugin_state})

            if response.status_code != 200:
                self.logger.error(f"Failed to {plugin_state} {current_service}.")
                statuses.append(False)
            else:
                self.logger.info(f"Switched {current_service} to be {plugin_state}.")
                statuses.append(True)

        return '' if all(statuses) else return_error(f'Failed to {plugin_state} all plugins', 500)

    @add_rule_unauthenticated("execution", methods=['GET'])
    def get_execution(self):
        services = ['execution', 'careful_execution_correlator_plugin', 'general-info-plugin']
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
