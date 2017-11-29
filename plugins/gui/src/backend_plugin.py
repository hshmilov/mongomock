"""
GUIPlugin.py: Backend services for the web app
"""

__author__ = "Mark Segal"

from axonius.PluginBase import PluginBase, add_rule, return_error
import tarfile
import io
from datetime import date
from flask import jsonify, request, session, after_this_request, send_from_directory
from passlib.hash import bcrypt
from elasticsearch import Elasticsearch
import requests
import configparser
import pymongo
from bson import SON, ObjectId
import os
import json
from datetime import timedelta, datetime

# the maximal amount of data a pagination query will give
PAGINATION_LIMIT_MAX = 100


# def add_rule_unauthenticated(rule, require_connected=True, *args, **kwargs):
#     """
#     Syntactic sugar for add_rule(should_authenticate=False, ...)
#     :param rule: rule name
#     :param require_connected: whether or not to require that the user is connected
#     :param args:
#     :param kwargs:
#     :return:
#     """
#     add_rule_res = add_rule(rule, should_authenticate=False, *args, **kwargs)
#     if require_connected:
#         return lambda func: requires_connected(add_rule_res(func))
#     return add_rule_res


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
            pass

            mongo_filter = request.args.get('filter')
            parsed_filter = dict()
            if mongo_filter:
                try:
                    mongo_filter = json.loads(mongo_filter)

                    def _create_regex(value):
                        """
                        Wrap value with a document that tell mongo to regard it as regex
                        :param value:
                        :return:
                        """
                        return {'$regex': value}

                    # TODO: Beautify by taking the $or case into an external method.
                    # If there are more than one filter, should be regarded as "and" logic
                    if len(mongo_filter) > 1:
                        parsed_filter['$and'] = []

                        for key, val in mongo_filter.items():
                            # If a value is a list, should be regarded as "or" logic
                            if isinstance(val, list):
                                or_list = {"$or": []}
                                for or_val in val:
                                    or_list["$or"].append(
                                        {key: _create_regex(or_val)})

                                parsed_filter['$and'].append(or_list)

                            else:
                                parsed_filter['$and'].append(
                                    {key: _create_regex(val)})

                    else:
                        mongo_filter_key = list(mongo_filter.keys())[0]
                        mongo_filter_value = list(mongo_filter.values())[0]

                        # If a value is a list, should be regarded as "or" logic
                        if isinstance(mongo_filter_value, list):

                            parsed_filter['$or'] = []
                            for or_val in mongo_filter_value:
                                parsed_filter["$or"].append(
                                    {mongo_filter_key: _create_regex(or_val)})

                        else:
                            parsed_filter[mongo_filter_key] = _create_regex(mongo_filter_value)

                except json.JSONDecodeError:
                    pass
            return func(self, mongo_filter=parsed_filter, *args, **kwargs)

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


# Caution! These decorators must come BEFORE @add_rule
def requires_aggregator():
    """
    Decorator stating that the view requires an aggregator DB
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            if self._aggregator_plugin_unique_name is None:
                return return_error("Aggregator is missing, try again later", 500)
            return func(self, *args, **kwargs)

        return actual_wrapper

    return wrap


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


class BackendPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        config = configparser.ConfigParser()
        config.read('plugin_config.ini')

        super().__init__(*args, **kwargs)
        # AXONIUS_REST.root_path = os.getcwd()
        # AXONIUS_REST.static_folder = 'my-project/dist/static'
        # AXONIUS_REST.static_url_path = 'static'
        # AXONIUS_REST.config['SESSION_TYPE'] = 'memcached'
        # AXONIUS_REST.config['SECRET_KEY'] = 'this is my secret key which I like very much, I have no idea what is this'
        aggregator = self._get_aggregator()
        if aggregator is None:
            self._aggregator_plugin_unique_name = None
        else:
            self._aggregator_plugin_unique_name = aggregator['plugin_unique_name']
            # self._elk_addr = config['gui_specific']['elk_addr']
            # self._elk_auth = config['gui_specific']['elk_auth']
            # self.db_user = config['gui_specific']['db_user']
            # self.db_password = config['gui_specific']['db_password']

    def _get_aggregator(self):
        # using requests directly so the gui key won't be sent, so the core will give a list of the plugins
        plugins_available = requests.get(
            self.core_address + '/register').json()
        aggregator_plugin = [x for x in plugins_available.values(
        ) if x['plugin_name'] == 'aggregator']
        if len(aggregator_plugin) == 0:
            return None
        if len(aggregator_plugin) != 1:
            raise RuntimeError(
                f"There are {len(aggregator_plugin)} aggregators, there should only be one")
        return aggregator_plugin[0]

    def _query_aggregator(self, resource, *args, **kwargs):
        """

        :param resource:
        :param args:
        :param kwargs:
        :return:
        """
        return self.request_remote_plugin(resource, self._aggregator_plugin_unique_name, *args, **kwargs).json()

    @add_rule("adapter_devices/<device_id>", should_authenticate=False)
    def adapter_device_by_id(self, device_id):
        """
        -- this has to be remade, postponed because it's not for MVP
        Returns a device by id
        :param device_id: device id
        :return:
        """
        with self._get_db_connection(False) as db_connection:
            parsed_db = db_connection[self._aggregator_plugin_unique_name]['parsed']
            device = parsed_db.find_one({'id': device_id}, sort=[
                ('_id', pymongo.DESCENDING)])
            if device is None:
                return return_error("Device not found", 404)
            return jsonify(beautify_db_entry(device))

    @requires_aggregator()
    @paginated()
    @filtered()
    @projectioned()
    @add_rule("adapter_devices", should_authenticate=False)
    def adapter_devices(self, limit, skip, mongo_filter, mongo_projection):
        """
        Returns all known devices. All parameters are generated by the decorators.
        :param limit: limit for pagination
        :param skip: start index for pagination
        :param fields: fields to return, or None for all
        :return:
        """
        if query is None:
            group_by = {"_id": "$data.id",
                        "all":
                            {"$first": "$$ROOT"}
                        }
        else:
            group_by = {field_name: {'$first': '$' + db_path}
                        for field_name, db_path in fields}
            group_by['_id'] = "$data.id"
            group_by['date_fetcher'] = {"$first": "$_id"}

        with self._get_db_connection(False) as db_connection:
            parsed_db = db_connection[self._devices_db_name]['parsed']
            devices = parsed_db.aggregate([
                {"$sort": SON([('_id', pymongo.DESCENDING)])},
                {
                    "$group": group_by
                },
                {"$sort": SON([('all.data.name', pymongo.ASCENDING)])},
                {"$skip": skip},
                {"$limit": limit}
            ])

            if query is None:
                return jsonify([beautify_db_entry(x['all']) for x in devices])
        return jsonify(devices)

    @requires_aggregator()
    @paginated()
    @filtered()
    @projectioned()
    @add_rule("devices", should_authenticate=False)
    def current_devices(self, limit, skip, mongo_filter, mongo_projection):
        """
        Get Axonius devices from the aggregator
        """
        with self._get_db_connection(True) as db_connection:
            client_collection = db_connection[self._aggregator_plugin_unique_name]['devices_db']
            device_list = client_collection.find(
                mongo_filter, mongo_projection)
            if mongo_filter and not skip:
                db_connection[self.plugin_unique_name]['queries'].insert_one(
                    {'filter': request.args.get('filter'), 'query_type': 'history', 'timestamp': datetime.now(),
                     'device_count': device_list.count() if device_list else 0, 'archived': False})
            return jsonify(beautify_db_entry(device) for device in
                           device_list.sort([('_id', pymongo.ASCENDING)]).skip(skip).limit(limit))

    @add_rule("devices/<device_id>", methods=['POST', 'GET'], should_authenticate=False)
    def current_device_by_id(self, device_id):
        """
        Retrieve device by the given id, from current devices DB or update it
        Currently, update works only for tags because that is the only edit operation user has
        :return:
        """
        with self._get_db_connection(True) as db_connection:
            if request.method == 'GET':
                return jsonify(db_connection[self._aggregator_plugin_unique_name]['devices_db'].find_one(
                    {'internal_axon_id': device_id}))
            elif request.method == 'POST':
                device_to_update = self.get_request_data_as_object()

                device = db_connection[self._aggregator_plugin_unique_name]['devices_db'].find_one(
                    {'internal_axon_id': device_id})

                associated_adapter_devices = {}

                for adapter in device['adapters']:
                    associated_adapter_devices[adapter['plugin_unique_name']] = adapter['data']['id']

                for current_tag in device_to_update['tags']:
                    update_data = {'association_type': 'Tag',
                                   'associated_adapter_devices': associated_adapter_devices,
                                   "tagname": current_tag,
                                   "tagvalue": current_tag}
                    response = self.request_remote_plugin(
                        'plugin_push', self._aggregator_plugin_unique_name, 'post', data=json.dumps(update_data))

                    if response != 200:
                        self.logger.error('Aggregator failed to tag device.')
                return '', 200

    @requires_aggregator()
    @add_rule("devices/fields", should_authenticate=False)
    def unique_fields(self):
        """
        Get all unique fields that devices may have data for, coming from the adapters' parsed data
        :return:
        """

        def _find_paths_to_strings(data, current_path):
            """
            Recursion to find full paths of string \ list field values
            :param data:
            :param current_path:
            :return:
            """
            if isinstance(data, dict):
                new_paths = []
                for current_key in data.keys():
                    new_paths.extend(_find_paths_to_strings(
                        data[current_key], '{0}.{1}'.format(current_path, current_key)))
                return new_paths
            return [current_path]

        all_fields = {}
        with self._get_db_connection(True) as db_connection:
            all_devices = list(
                db_connection[self._aggregator_plugin_unique_name]['devices_db'].find())
            for current_device in all_devices:
                for current_adapter in current_device['adapters']:
                    all_fields[current_adapter['plugin_name']] = _find_paths_to_strings(
                        current_adapter['data']['raw'], 'adapters.data.raw')

        return jsonify(all_fields)

    @requires_aggregator()
    @add_rule("devices/tags", should_authenticate=False)
    def tags(self):
        """
        Get all tags that currently belong to devices, to form a set of current tag values
        :return:
        """
        all_tags = set()
        with self._get_db_connection(True) as db_connection:
            client_collection = db_connection[self._aggregator_plugin_unique_name]['devices_db']

            for current_device in client_collection.find({"tags.tagname": {"$exists": True}}):
                for current_tag in current_device['tags']:
                    all_tags.add(current_tag['tagname'])

        return jsonify(all_tags)

    @paginated()
    @filtered()
    @add_rule("queries", methods=['POST', 'GET'], should_authenticate=False)
    def queries(self, limit, skip, mongo_filter):
        """
        Get and create saved filters.
        A filter is a query to run on the devices.
        Only helps the UI show "last queries", doesn't perform any action.
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        queries_collection = self._get_collection('queries')
        if request.method == 'GET':
            mongo_filter['archived'] = False
            return jsonify(beautify_db_entry(entry) for entry in queries_collection.find(mongo_filter)
                           .sort([('_id', pymongo.DESCENDING)])
                           .skip(skip).limit(limit))
        if request.method == 'POST':
            query_to_add = request.get_json(silent=True)
            if query_to_add is None:
                return return_error("Invalid query", 400)
            query_data, query_name = query_to_add.get(
                'filter'), query_to_add.get('name')
            result = queries_collection.insert_one(
                {'filter': json.dumps(query_data), 'name': query_name, 'query_type': 'saved',
                 'timestamp': datetime.now(), 'archived': False})
            return str(result.inserted_id), 200

    @add_rule("queries/<query_id>", methods=['DELETE'], should_authenticate=False)
    def delete_query(self, query_id):
        queries_collection = self._get_collection('queries')
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
    @add_rule("adapters", should_authenticate=False)
    def adapters(self, mongo_filter):
        """
        Get all adapters from the core
        :mongo_filter
        :return:
        """
        plugins_available = self.request_remote_plugin('register').json()
        with self._get_db_connection(False) as db_connection:
            adapters_from_db = db_connection['core']['configs'].find({'plugin_type': 'Adapter'}).sort(
                [('plugin_unique_name', pymongo.ASCENDING)])
            return jsonify({'name': adapter['plugin_name'],
                            'id': adapter['plugin_unique_name'],
                            'state': 'success' if (adapter['plugin_unique_name'] in plugins_available) else 'error',
                            'schema': self._get_plugin_schemas(db_connection, adapter['plugin_unique_name'])
                            }
                           for adapter in
                           adapters_from_db)

    @paginated()
    @add_rule("adapters/<adapter_unique_name>/clients", methods=['POST', 'GET'], should_authenticate=False)
    def adapters_clients(self, adapter_unique_name, limit, skip):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param limit: for pagination (only for GET)
        :param skip: for pagination (only for GET)
        :return:
        """
        with self._get_db_connection(False) as db_connection:
            client_collection = db_connection[adapter_unique_name]['clients']
            if request.method == 'GET':
                return jsonify(
                    beautify_db_entry(client) for client in
                    client_collection.find().sort([('_id', pymongo.ASCENDING)]).skip(
                        skip).limit(limit))
            if request.method == 'POST':
                client_to_add = request.get_json(silent=True)
                if client_to_add is None:
                    return return_error("Invalid client", 400)
                client_to_add['archived'] = False
                result = client_collection.insert(client_to_add)
                return str(result.inserted_id), 200

    @add_rule("adapters/<adapter_unique_name>/clients/<client_id>", methods=['POST', 'DELETE'],
              should_authenticate=False)
    def adapters_clients_update(self, adapter_unique_name, client_id):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param client_id: UUID of client to delete
        :return:
        """
        with self._get_db_connection(False) as db_connection:
            client_collection = db_connection[adapter_unique_name]['clients']
            if request.method == 'POST':
                client_to_update = request.get_json(silent=True)
                client_collection.update_one({'_id': ObjectId(client_id)}, {
                    '$set': client_to_update
                })
            if request.method == 'DELETE':
                db_connection[adapter_unique_name]['clients'].update_one(
                    {'_id': ObjectId(client_id)}, {'$set': {'archived': True}})
            return ""

    @add_rule("config/<config_name>", methods=['POST', 'GET'], should_authenticate=False)
    def config(self, config_name):
        """
        Get or set config by name
        :param config_name: Config to fetch
        :return:
        """
        configs_collection = self._get_collection('config')
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
    @add_rule("notifications", methods=['POST', 'GET'], should_authenticate=False)
    def notifications(self, limit, skip):
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
                               notification_collection.find(projection={
                                   "_id": 1,
                                   "who": 1,
                                   "plugin_name": 1,
                                   "type": 1,
                                   "title": 1,
                                   "seen": 1}).sort(
                                   [('_id', pymongo.ASCENDING)]).skip(skip).limit(limit))
            elif request.method == 'POST':
                notifications_to_see = request.get_json(silent=True)
                if notifications_to_see is None:
                    return return_error("Invalid notification list", 400)
                update_result = notification_collection.update_many(
                    {"_id": {"$in": [ObjectId(x) for x in notifications_to_see.get('notification_ids', [])]}
                     }, {"$set": {'seen': notifications_to_see.get('seen', True)}})
                return str(update_result.modified_count), 200

    @add_rule("notifications/<notification_id>", methods=['GET'], should_authenticate=False)
    def notifications_by_id(self, notification_id):
        """
        Get all notification data
        :param notification_id: Notification ID
        :return:
        """
        with self._get_db_connection(False) as db:
            notification_collection = db['core']['notifications']
            return jsonify(notification_collection.find_one({'_id': notification_id}))

    @add_rule("login", methods=['GET', 'POST'], should_authenticate=False)
    def login(self):
        """
        Get current user or login
        :return:
        """
        if request.method == 'GET':
            user = session.get('user')
            if user is None:
                return return_error("Not logged in", 401)
            return jsonify(user['username']), 200

        users_collection = self._get_collection('users')
        log_in_data = request.get_json(silent=True)
        if log_in_data is None:
            return return_error("No login data provided", 400)
        username = log_in_data.get('username')
        password = log_in_data.get('password')
        user_from_db = users_collection.find_one({'username': username})
        if user_from_db is None:
            return return_error("No such username", 401)
        if not bcrypt.verify(password, user_from_db['password']):
            return return_error("Wrong password", 401)
        session['user'] = user_from_db
        return ""

    @add_rule("logout", methods=['GET'], should_authenticate=False)
    def logout(self):
        """
        Clears session, logs out
        :return:
        """
        session['user'] = None
        return ""

    @paginated()
    @add_rule("users", methods=['GET', 'POST'], should_authenticate=False)
    def users(self, limit, skip):
        """
        View or add users
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        users_collection = self._get_collection('users')
        if request.method == 'GET':
            return jsonify(beautify_db_entry(n) for n in
                           users_collection.find(projection={
                               "_id": 1,
                               "username": 1,
                               "firstname": 1,
                               "lastname": 1,
                               "picname": 1}).sort(
                               [('_id', pymongo.ASCENDING)]).skip(skip).limit(limit))
        elif request.method == 'POST':
            user_data = request.get_json(silent=True)
            users_collection.update({'username': user_data['username']},
                                    {'username': user_data['username'],
                                     'first_name': user_data.get('firstname'),
                                     'last_name': user_data.get('lastname'),
                                     'pic_name': user_data.get('picname'),
                                     'password': bcrypt.hash(user_data['password']),
                                     },
                                    upsert=True)
            return "", 201

    @paginated()
    @add_rule("logs", should_authenticate=False)
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
