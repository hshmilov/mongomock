from datetime import timedelta, datetime

from flask import Flask, send_from_directory, request, jsonify, make_response, json, current_app, render_template
from bson import ObjectId
from functools import update_wrapper
import pymongo
import threading
import time
import random
import uuid

sample_rate = 10
time_to_die = 24
plugin_state = False

now_date = datetime.strptime(
    '2017-11-12 20:21:44.539418', '%Y-%m-%d %H:%M:%S.%f')


class IteratorJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o.generation_time)
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        return json.JSONEncoder.default(self, o)


app = Flask(__name__)
app.json_encoder = IteratorJSONEncoder

mongo_client = pymongo.MongoClient(
    host='localhost', port=27017, username='ax_user', password='IAmDeanSysMan')


@app.after_request
def add_header(r):
    """
    Disables caching.
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    r.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return r


def auto_options(attach_to_all=True,
                 automatic_options=True):
    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)

    return decorator


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


def query_item(current_device_list, query):
    def _recursive_find_key_val_pair_in_dict(current_dict, key, val):
        # Check if the current dict contains the key and if so check if
        # it's value (Creates the logic of "Like" for strings).
        if '.' in key:
            # Should search for a specific key
            all_address = key.split('.')
            current_value = current_dict['adapters']
            for one_addr in all_address:
                current_value = current_value.get(one_addr, None)
                if not current_value:
                    return False
            if val in current_value:
                return True
            else:
                return False
        if key in current_dict.keys():
            if key == 'tags':
                if val in current_dict['tags']:
                    return True
            return val in current_dict[key]
        else:
            # If current dict doesn't contain the key go recursively on each.
            for k, v in current_dict.items():
                if isinstance(v, dict):
                    item = _recursive_find_key_val_pair_in_dict(v, key, val)
                    if item is not None:
                        return item

    # Go through the query and filter items out of all the devices one by one
    for key, value in query.items():
        # If the current value of the query is a list then go through it one by one and filter.
        if isinstance(value, list):
            for nested_value in value:
                current_device_list = [current_device for current_device in current_device_list if
                                       _recursive_find_key_val_pair_in_dict(current_device, key, nested_value)]
        else:
            current_device_list = [current_device for current_device in current_device_list if
                                   _recursive_find_key_val_pair_in_dict(current_device, key, value)]
    return current_device_list


@app.route('/api/devices')
@auto_options()
def devices():
    """
    Returns all known devices. All parameters are generated by the decorators.
    :return:
    """

    skip = int(request.args.get('skip', 0))
    limit = int(request.args.get('limit', 100))
    filter = request.args.get('filter', None)

    client_collection = mongo_client['aggregator_plugin']['devices_db_2']
    device_list = list(client_collection.find().sort(
        [('_id', pymongo.ASCENDING)]))
    if filter is not None:
        device_list = query_item(device_list, json.loads(filter))
        if skip == 0:
            mongo_client['api']['queries'].insert_one(
                {'query': filter, 'query_type': 'history', 'timestamp': datetime.now(),
                 'device_count': len(device_list)})

    return make_response(jsonify(beautify_db_entry(device) for device in device_list[skip:(skip + limit)]))


@auto_options()
@app.route('/api/devices/<device_id>', methods=['POST', 'GET'])
def device_by_id(device_id):
    """
    Returns a device by id
    :param device_id: device id
    :return:
    """

    def _get_device_by_id_from_db(device_id):
        return mongo_client['aggregator_plugin']['devices_db_2'].find_one({'internal_axon_id': device_id})

    if request.method == 'GET':
        return jsonify(_get_device_by_id_from_db(device_id))
    elif request.method == 'POST':
        data = json.loads(request.data.decode('utf-8'))

        device_data = _get_device_by_id_from_db(device_id)
        device_data['tags'] = data['tags']
        mongo_client['aggregator_plugin']['devices_db_2'].update_one({'internal_axon_id': device_id},
                                                                     {'$set': {'tags': device_data['tags']}})

        return '', 200


@app.route('/api/tags')
@auto_options()
def tags():
    client_collection = mongo_client['aggregator_plugin']['devices_db_2']

    return jsonify(
        [current_tag for current_tag in client_collection.find({}, {'tags': True, '_id': False}).distinct("tags")
         if len(current_tag) != 0])


@app.route('/api/plugins')
@auto_options()
def plugins():
    return jsonify(['Correlator', 'Discovery', 'QCoreCheckPointBlocker'])


@auto_options()
@app.route('/api/plugins/<plugin_id>', methods=['POST', 'GET'])
def plugins_configuration(plugin_id):
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if data is None:
            return "basa mamash"
        global time_to_die
        global plugin_state
        time_to_die = int(data['time_to_die'])
        plugin_state = data['plugin_state']

        if (plugin_state is True):
            plugin_start("QCoreCheckPointBlocker")
        else:
            plugin_stop("QCoreCheckPointBlocker")

        return "ok"
    if plugin_id == 'QCoreCheckPointBlocker':
        to_return = {}

        to_return['parameters'] = {'sample_rate': (sample_rate, 'int'),  # In seconds
                                   'time_to_die': (time_to_die, 'int'),
                                   'plugin_state': (plugin_state, 'bool')}

        client_collection = mongo_client['aggregator_plugin']['devices_db_2']
        all_devices = client_collection.find({'$or': [{'adapters.qcore_adapter.plugin_name': 'qcore_adapter'},
                                                      {
                                                          'adapters.splunk_adapter.data.raw.report_issuer': 'q-core device'}]})
        qcore_devices = all_devices.count()
        all_devices = client_collection.find({'$and': [{'$or': [{'adapters.qcore_adapter.plugin_name': 'qcore_adapter'},
                                                                {
                                                                    'adapters.splunk_adapter.data.raw.report_issuer': 'q-core device'}]},
                                                       {'adapters.checkpoint_adapter.data.raw.status': 'Blocked'}]})
        blocked_devices = all_devices.count()

        all_devices = client_collection.find({'$and': [{'$or': [{'adapters.qcore_adapter.plugin_name': 'qcore_adapter'},
                                                                {
                                                                    'adapters.splunk_adapter.data.raw.report_issuer': 'q-core device'}]},
                                                       {'adapters.checkpoint_adapter.data.raw.status': 'Unblocked'}]})
        unblocked_devices = all_devices.count()

        to_return['data'] = {'qcore_devices': qcore_devices - blocked_devices,
                             'blocked_devices': blocked_devices,
                             'reappearing_devices': unblocked_devices}
        return jsonify(to_return)


def start_qcore_plugin():
    while True:
        try:
            client_collection = mongo_client['aggregator_plugin']['devices_db_2']
            all_devices = client_collection.find({'$or': [{'adapters.qcore_adapter.plugin_name': 'qcore_adapter'},
                                                          {
                                                              'adapters.splunk_adapter.data.raw.report_issuer': 'q-core device'}]})
            for device in all_devices:
                if 'qcore_adapter' in device['adapters']:
                    last_time = device['adapters']['qcore_adapter']['accurate_for_datetime']
                    current_ip = device['adapters']['qcore_adapter']['data']['IP']
                    current_id = device['adapters']['qcore_adapter']['data']['pretty_id']
                    last_connected = datetime.strptime(
                        last_time, '%Y-%m-%d %H:%M:%S.%f')
                elif 'splunk_adapter' in device['adapters']:
                    last_time = device['adapters']['splunk_adapter']['accurate_for_datetime']
                    current_ip = device['adapters']['splunk_adapter']['data']['IP']
                    current_id = device['adapters']['splunk_adapter']['data']['pretty_id']
                    last_connected = datetime.strptime(
                        last_time, '%Y-%m-%d %H:%M:%S.%f')
                else:
                    last_connected = now_date

                if last_connected < now_date - timedelta(hours=time_to_die):
                    # Should 'block' device
                    if 'checkpoint_adapter' in device['adapters']:
                        if device['adapters']['checkpoint_adapter']['data']['raw']['status'] == 'Blocked':
                            # Device already blocked
                            continue
                    else:
                        # Build checkpoint adapter data
                        checkpoint_data = {'client_used': 'checkpoint_controller',
                                           'plugin_type': 'Adapter',
                                           'plugin_name': 'checkpoint_adapter',
                                           'unique_plugin_name': 'checkpoint_adapter_1',
                                           'accurate_for_datetime': str(datetime.now()),
                                           '_id': uuid.uuid4().hex}
                        checkpoint_data['data'] = {'IP': current_ip,
                                                   'pretty_id': current_id}
                        checkpoint_data['data']['raw'] = {'status': 'Blocked'}

                        device['adapters']['checkpoint_adapter'] = checkpoint_data

                        client_collection.replace_one(
                            {'_id': device['_id']}, device)
                else:
                    # Check if we should unblock device
                    if 'checkpoint_adapter' in device['adapters']:
                        if device['adapters']['checkpoint_adapter']['data']['raw']['status'] == 'Blocked':
                            # Changing the status to unblocked
                            device['adapters']['checkpoint_adapter']['data']['raw']['status'] = 'Unblocked'
                            client_collection.replace_one(
                                {'_id': device['_id']}, device)

        except Exception as e:
            print('Exception ' + str(e))
            pass
        finally:
            time.sleep(sample_rate)


@app.route('/api/plugins/<plugin_id>/start')
@auto_options()
def plugin_start(plugin_id):
    global plugin_state
    plugin_state = True
    if plugin_id == 'QCoreCheckPointBlocker':
        threading.Thread(target=start_qcore_plugin).start()
    return ''


@app.route('/api/plugins/<plugin_id>/stop')
@auto_options()
def plugin_stop(plugin_id):
    global plugin_state
    plugin_state = False
    return ''


@app.route('/api/queries', methods=['GET', 'POST'])
@auto_options()
def queries():
    if request.method == 'GET':
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', 100))
        filter_str = request.args.get('filter')
        filter = json.loads(filter_str) if filter_str else {}
        filter['archived'] = { '$exists': False }
        result = mongo_client['api']['queries'].find(filter).sort([('_id', pymongo.DESCENDING)]).skip(skip)
        if limit > 0:
            result = result.limit(limit)
        queryList = []
        for doc in result:
            if doc.get('query'):
                queryList.append({'id': str(doc['_id']),
                                  'query_name': doc['query_name'] if doc.get('query_name') else '',
                                  'timestamp': doc['timestamp'], 'query': doc['query'],
                                  'device_count': doc['device_count'] if doc.get('device_count') else 0})
        return jsonify(queryList)
    elif request.method == 'POST':
        data = json.loads(request.data.decode('utf-8'))
        result = mongo_client['api']['queries'].insert_one(
            {'query': json.dumps(data['query']), 'query_type': 'saved', 'timestamp': datetime.now(),
             'query_name': data['name']})
        return str(result.inserted_id), 200


@app.route('/api/queries/<query_id>', methods=['DELETE'])
@auto_options()
def archive_query(query_id):
    mongo_client['api']['queries'].update_one(
        {'_id': ObjectId(query_id)},
        {'$set': {'archived': True}})
    return '', 200


@app.route('/api/fields')
@auto_options()
def get_all_fields():
    all_fields = set()
    cursor = list(mongo_client['aggregator_plugin']['devices_db_2'].find())
    for current_document in cursor:
        for current_adapter in current_document['adapters'].keys():
            for current_raw_field in current_document['adapters'][current_adapter]['data']['raw'].keys():
                all_fields.add(
                    '.'.join([current_adapter, 'data', 'raw', current_raw_field]))

    for current_document in cursor:
        for current_adapter in current_document['adapters'].keys():
            all_fields.discard('.'.join([current_adapter, 'data']))
            all_fields.discard('.'.join([current_adapter, 'data', 'raw']))

    return jsonify(all_fields)


@app.route('/api/alerts', methods=['GET', 'POST'])
@auto_options()
def alerts():
    if request.method == 'GET':
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', 100))
        filter_str = request.args.get('filter')
        filter = json.loads(filter_str) if filter_str else {}
        filter['archived'] = { '$exists': False }
        result = mongo_client['api']['alerts'].find(filter).sort([('_id', pymongo.DESCENDING)]).skip(skip)
        if limit:
            result = result.limit(limit)
        alertList = []
        for doc in result:
            alertList.append({ 'id': str(doc['_id']),
                               'name': doc['name'] if doc.get('name') else '', 'timestamp': doc['timestamp'],
                               'criteria': doc['criteria'], 'query': doc['query'], 'retrigger': doc['retrigger'],
                               'notification': doc['action']['notification'] if doc.get('action') else False })
        return jsonify(alertList)
    elif request.method == 'POST':
        data = json.loads(request.data.decode('utf-8'))
        result = mongo_client['api']['alerts'].insert_one({
            'query': json.dumps(data['query']), 'type': 'Manual', 'timestamp': datetime.now(),
            'name': data['name'], 'criteria': data['criteria'], 'notification': data['action']['notification'],
            'retrigger': data['retrigger']
        })
        return str(result.inserted_id), 200


@app.route('/api/alerts/<alert_id>', methods=['DELETE', 'POST', 'GET'])
@auto_options()
def edit_alert(alert_id):
    if request.method == 'GET':
        doc = mongo_client['api']['alerts'].find({'_id': ObjectId(alert_id)})[0]
        return jsonify({
            'id': str(doc['_id']),
            'name': doc['name'] if doc.get('name') else '', 'timestamp': doc['timestamp'],
            'criteria': doc['criteria'], 'query': doc['query'], 'retrigger': doc['retrigger'],
            'notification': doc['action']['notification'] if doc.get('action') else False
        })
    elif request.method == 'DELETE':
        mongo_client['api']['alerts'].update_one(
            {'_id': ObjectId(alert_id)},
            {'$set': {'archived': True}}
        )
        return '', 200
    elif request.method == 'POST':
        data = json.loads(request.data.decode('utf-8'))
        result = mongo_client['api']['alerts'].update_one(
            {'_id': ObjectId(alert_id)},
            {
                'query': json.dumps(data['query']), 'type': 'Manual', 'timestamp': datetime.now(),
                'name': data['name'], 'criteria': data['criteria'], 'notification': data['action']['notification'],
                'retrigger': data['retrigger']
            }
        )
        return str(result.inserted_id), 200


@app.route('/src/<path:filename>')
def custom_static_src(filename):
    return send_from_directory("src", filename)


@app.route('/dist/<path:filename>')
def custom_static_dist(filename):
    return send_from_directory("dist", filename)


@app.route('/node_modules/<path:filename>')
def custom_static_modules(filename):
    return send_from_directory("node_modules", filename)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return render_template("index.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1337)
