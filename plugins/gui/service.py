from axonius.utils.files import get_local_config_file
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.devices.device import Device
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, PLUGIN_NAME, AGGREGATOR_PLUGIN_NAME, SYSTEM_SCHEDULER_PLUGIN_NAME
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
import pql
from datetime import datetime

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
    Decorator stating that the view supports ?filter={"plugin_name":"aws_adapter" ,"data.name": ["WINDOWS8", "Blah"]}
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            filter_obj = dict()
            try:
                filter_expr = request.args.get('filter')
                if filter_expr:
                    self.logger.info("Parsing filter: {0}".format(filter_expr))
                    filter_obj = pql.find(filter_expr)
            except pql.matching.ParseError as e:
                return return_error("Could not parse given expression. Details: {0}".format(e), 400)
            except Exception as e:
                return return_error("Could not create mongo filter. Details: {0}".format(e), 400)
            return func(self, mongo_filter=filter_obj, *args, **kwargs)

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
        self.add_default_queries()

    @paginated()
    @filtered()
    @projectioned()
    @add_rule_unauthenticated("devices")
    def current_devices(self, limit, skip, mongo_filter, mongo_projection):
        """
        Get Axonius devices from the aggregator
        """
        with self._get_db_connection(False) as db_connection:
            device_list = db_connection[AGGREGATOR_PLUGIN_NAME]['devices_db_view'].find(mongo_filter, mongo_projection)
            if mongo_filter and not skip:
                db_connection[self.plugin_unique_name]['queries'].insert_one(
                    {'filter': request.args.get('filter'), 'query_type': 'history', 'timestamp': datetime.now(),
                     'device_count': device_list.count() if device_list else 0, 'archived': False})
            return jsonify(beautify_db_entry(device) for device in
                           device_list.sort([('_id', pymongo.ASCENDING)]).skip(skip).limit(limit))

    @filtered()
    @add_rule_unauthenticated("devices/count", methods=['GET'])
    def current_devices_count(self, mongo_filter):
        """
        Count total number of devices answering given mongo_filter

        :param mongo_filter: Object defining a Mongo query
        :return: Number of devices
        """
        with self._get_db_connection(False) as db_connection:
            client_collection = db_connection[AGGREGATOR_PLUGIN_NAME]['devices_db_view']
            return str(client_collection.find(mongo_filter, {'_id': 1}).count())

    @add_rule_unauthenticated("devices/<device_id>", methods=['GET'])
    def current_device_by_id(self, device_id):
        """
        Retrieve device by the given id, from current devices DB or update it
        Currently, update works only for tags because that is the only edit operation user has
        :return:
        """
        with self._get_db_connection(False) as db_connection:
            device = db_connection[AGGREGATOR_PLUGIN_NAME]['devices_db_view'].find_one(
                {'internal_axon_id': device_id})
            if device is None:
                return return_error("Device ID wasn't found", 404)
            return jsonify(device)

    @add_rule_unauthenticated("devices/fields")
    def device_fields(self):
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
            plugins_from_db = db_connection['core']['configs'].find({}).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            for plugin in plugins_from_db:
                if db_connection[plugin[PLUGIN_UNIQUE_NAME]]['fields']:
                    plugin_fields_record = db_connection[plugin[PLUGIN_UNIQUE_NAME]]['fields'].find_one(
                        {'name': 'parsed'}, projection={'schema': 1})
                    if plugin_fields_record:
                        fields['specific'][plugin[PLUGIN_NAME]] = _censor_fields(plugin_fields_record['schema'])

        return jsonify(fields)

    @add_rule_unauthenticated("devices/labels", methods=['GET', 'POST', 'DELETE'])
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

            responses = []
            for device_id in devices_and_labels['devices']:
                device = devices_collection.find_one({'internal_axon_id': device_id})

                # We tag that device with a correlation to its first adapter. In case of a split,
                # We should know this tag is a "gui" tag since the tag issuer ("tags.plugin_name") is "gui".
                # TODO: have a key that says this is a "global" tag that should be equally split when we get
                # TODO: a split situation.

                device_identity = device['adapters'][0]['plugin_unique_name'], device['adapters'][0]['data']['id']
                for label in devices_and_labels['labels']:
                    responses.append(
                        self.add_label_to_device(device_identity, label, True if request.method == 'POST' else False))

            all_bad_responses = [current_response.json()
                                 for current_response in responses if current_response.status_code != 200]

            if len(all_bad_responses) > 0:
                self.logger.error(f"Tagging did not complete. First error: {all_bad_responses[0]}")
                return_error(f'Tagging did not complete. First error: {all_bad_responses[0]}', 400)
            return '', 200

    @paginated()
    @filtered()
    @add_rule_unauthenticated("queries", methods=['POST', 'GET'])
    def queries(self, limit, skip, mongo_filter):
        """
        Get and create saved filters.
        A filter is a query to run on the devices.
        Only helps the UI show "last queries", doesn't perform any action.
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        if request.method == 'GET':
            mongo_filter['archived'] = False
            queries_collection = self._get_collection('queries', limited_user=False)
            return jsonify(beautify_db_entry(entry) for entry in queries_collection.find(mongo_filter)
                           .sort([('_id', pymongo.DESCENDING)])
                           .skip(skip).limit(limit))
        if request.method == 'POST':
            query_to_add = request.get_json(silent=True)
            if query_to_add is None:
                return return_error("Invalid query", 400)
            inserted_id = self._insert_query(query_to_add.get('name'), query_to_add.get('filter'))
            return str(inserted_id), 200

    def _insert_query(self, name, query_filter):
        queries_collection = self._get_collection('queries', limited_user=False)
        existed_query = queries_collection.find_one({'filter': query_filter, 'name': name})
        if existed_query is not None:
            self.logger.info(f'Query {name} already exists id: {existed_query["_id"]}')
            return existed_query['_id']
        result = queries_collection.update({'name': name}, {'$set': {'filter': query_filter, 'name': name,
                                                                     'query_type': 'saved', 'timestamp': datetime.now(),
                                                                     'archived': False}}, upsert=True)
        self.logger.info(f'Added query {name} id: {result.get("inserted_id", "")}')
        return result.get('inserted_id', '')

    def add_default_queries(self):
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
                    self._insert_query(name, query['query'])
                except:
                    self.logger.exception(f'Error adding default query {name}')
        except:
            self.logger.exception(f'Error adding default queries')

    @add_rule_unauthenticated("queries/<query_id>", methods=['DELETE'])
    def delete_query(self, query_id):
        queries_collection = self._get_collection('queries', limited_user=False)
        queries_collection.update({'_id': ObjectId(query_id)},
                                  {
                                      '$set': {
                                          'archived': True
                                      }}
                                  )
        return ""

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
                                client_collection.find().sort([('_id', pymongo.ASCENDING)])
                                .skip(skip).limit(limit)]
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

    @add_rule_unauthenticated("alerts", methods=['GET', 'PUT'])
    def alerts(self):
        """
        GET results in list of all currently configured alerts, with their query id they were created with
        PUT Send watch_service a new alert to be configured

        :return:
        """
        queries_collection = self._get_collection('queries', limited_user=False)
        if request.method == 'GET':
            with self._get_db_connection(False) as db_connection:
                alerts_to_return = []
                watch_service = self.get_plugin_by_name('watch_service')
                for alert in db_connection[watch_service[PLUGIN_UNIQUE_NAME]][
                        'watches'].find().sort(
                        [('watch_time', pymongo.DESCENDING)]):
                    # Fetching query in order to replace the string saved for aler
                    #  with the corresponding id that the UI can recognize the query as
                    query = queries_collection.find_one({'alertIds': {'$in': [str(alert['_id'])]}})
                    if query is None:
                        continue
                    alert['query'] = str(query['_id'])
                    alerts_to_return.append(beautify_db_entry(alert))
                return jsonify(alerts_to_return)

        if request.method == 'PUT':
            alert_to_add = request.get_json(silent=True)
            match_query = {'_id': ObjectId(alert_to_add['query'])}
            query = queries_collection.find_one(match_query)
            if query is None or not query.get('filter'):
                return return_error("Invalid query id {0} requested for creating alert".format(alert_to_add['query']))

            self.logger.info("About to watch the filter: {0}".format(query['filter']))
            alert_to_add['query'] = pql.find(query['filter'])
            response = self.request_remote_plugin("watch", "watch_service", method='put', json=alert_to_add)
            if response is not None and response.status_code == 201:
                # Updating saved query with the created alert's id, for reference when fetching alerts
                alert_ids = set(query.get('alertIds') or [])
                alert_ids.add(response.text)
                queries_collection.update_one(match_query, {'$set': {'alertIds': list(alert_ids)}})
            return response.text, response.status_code

    @add_rule_unauthenticated("alerts/<alert_id>", methods=['DELETE', 'POST'])
    def alerts_update(self, alert_id):
        """

        :param alert_id:
        :return:
        """
        queries_collection = self._get_collection('queries', limited_user=False)
        if request.method == 'DELETE':
            response = self.request_remote_plugin("watch/{0}".format(alert_id), "watch_service", method='delete')
            if response is None:
                return return_error("No response whether alert was removed")
            if response.status_code == 200:
                query = queries_collection.find_one({'alertIds': {'$in': [alert_id]}})
                if query is not None:
                    alert_ids = set(query.get('alertIds') or [])
                    alert_ids.remove(alert_id)
                    queries_collection.update_one({'_id': query['_id']}, {'$set': {'alertIds': list(alert_ids)}})
                    self.logger.info("Removed alert from containing query {0}".format(query['_id']))
            return response.text, response.status_code

        if request.method == 'POST':
            alert_to_update = request.get_json(silent=True)
            match_query = {'_id': ObjectId(alert_to_update['query'])}
            query = queries_collection.find_one(match_query)
            if query is None or not query.get('filter'):
                return return_error(
                    "Invalid query id {0} requested for creating alert".format(alert_to_update['query']))

            alert_to_update['query'] = pql.find(query['filter'])
            response = self.request_remote_plugin("watch/{0}".format(alert_id), "watch_service", method='post',
                                                  json=alert_to_update)
            if response is None:
                return return_error("No response whether alert was updated")

            if response.status_code == 200:
                # Remove alert from any queries holding it now
                query = queries_collection.find_one({'alertIds': {'$in': [alert_id]}})
                if query is not None:
                    alert_ids = set(query.get('alertIds') or [])
                    alert_ids.remove(alert_id)
                    queries_collection.update_one({'_id': query['_id']}, {'$set': {'alertIds': list(alert_ids)}})
                # Updating saved query with the created alert's id, for reference when fetching alerts
                alert_ids = set(query.get('alertIds') or [])
                alert_ids.add(response.text)
                queries_collection.update_one(match_query, {'$set': {'alertIds': list(alert_ids)}})

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

    @add_rule_unauthenticated("plugins/<plugin_unique_name>", methods=['GET'])
    def get_plugin(self, plugin_unique_name):
        """
        Gather all data needed to present a single plugin, according to plugin_unique_name given in url

        Currently implemented only for dns-conflicts plugin

        :return: Dict containing the data according to plugin's schema for UI presentation
        """
        if "dns_conflicts" not in plugin_unique_name:
            return return_error("Requested plugin not found or not yet implemented", 404)
        state = "Disabled"
        response = self.request_remote_plugin("state", plugin_unique_name)
        if response.status_code == 200:
            state = response.json()

        with self._get_db_connection(False) as db_connection:
            return jsonify({
                PLUGIN_UNIQUE_NAME: plugin_unique_name,
                'state': state,
                'results': [beautify_db_entry(device) for device in
                            db_connection[AGGREGATOR_PLUGIN_NAME]['devices_db'].find(
                                {'tags.name': "Ip Conflicts", 'tags.type': "data"},
                                projection={'adapters.data.pretty_id': 1, 'tags': 1, 'adapters.data.hostname': 1}).sort(
                                [('_id', pymongo.ASCENDING)])]
            })

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
                                   "severity": 1}).sort(
                                   [('_id', pymongo.DESCENDING)]).skip(skip).limit(limit))
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

    @add_rule_unauthenticated("dashboard/lifecycle", methods=['GET'])
    def get_system_lifecycle(self):
        """
        Fetches and build data needed for presenting current status of the system's lifecycle in a graph

        :return: Data containing:
         - All research phases names, for showing the whole picture
         - Current research phase, which is empty if system is not stable
         - Estimated time remaining for the current phase
         - The time next cycle is scheduled for
        """
        response = self.request_remote_plugin('state', SYSTEM_SCHEDULER_PLUGIN_NAME, method='get')
        if not response or not response.status_code:
            return return_error("Error fetching status of system scheduler")
        if response.status_code != 200:
            return return_error(f"Error fetching status of system scheduler. Reason: {response.json()}")

        state = response.json()
        current_stage = ''
        current_status = 0
        if state[StateLevels.Phase.name] != Phases.Stable.name:
            current_stage = state[StateLevels.SubPhase.name]
            current_status = state[StateLevels.SubPhaseStatus.name]

        # TODO get next cycle time
        return jsonify({'stages': [phase.name for phase in list(ResearchPhases)],
                        'current_stage': current_stage, 'current_status': current_status, 'next_cycle_time': ''})

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
                                                                              {'plugin_type': 'ScannerAdapter'}]}).sort(
                [(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
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

    @property
    def plugin_subtype(self):
        return "Core"
