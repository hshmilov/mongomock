"""ExecutionPlugin.py: Implementation of the Execution Plugin."""

__author__ = "Ofir Yefet"

from flask import jsonify
import threading
import json
from bson.objectid import ObjectId
import concurrent.futures

from axonius.PluginBase import PluginBase, add_rule
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME

PLUGIN_TYPE = 'execution_controller'


class ExecutionPlugin(PluginBase):
    """ A class containing all the Code execution management.

    Check PluginBase documentation for additional params and exception details.

    """

    # Functions
    def __init__(self, **kargs):
        """Class initialization.

        Will restore old actions from db

        """

        # Initialize the base plugin (will initialize http server)
        super().__init__(**kargs)

        self._actions_db = dict()

        # Restore old actions list
        self._restore_actions_from_db()

        # Threadpool for creating new actions
        self._actions_thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=20)

    def _restore_actions_from_db(self):
        """ Restores actions from db.

        Will only restore actions that are not finished. If an action is on 'started' mode than it will become 
        A 'limbo' action
        """
        actions_collection = self._get_collection('actions')
        # Getting all the actions from db
        all_actions = actions_collection.find({"$and": [{"status": {"$ne": "finished"}},
                                                        {"status": {
                                                            "$ne": "failed"}},
                                                        {"status": {"$ne": "limbo"}}]})
        for action in all_actions:
            action_id = str(action['_id'])
            del action['_id']
            if action['status'] == 'pending':
                # Action didnt start yet, then we may think of it as failed action
                action['status'] = 'failed'
            else:
                # We cant know the status of the action. If the adapter is still up,
                # It will update the state itself.
                action['status'] = 'limbo'
            # Saving the new action state
            self._save_action_data(action, action_id)

    def _find_adapters_for_action(self, device_id):
        """ This function should find the right adapters for executing actions

        The function will use the data saved on the devices db in order to find the best adapters for running code

        :param str device_id: The Axon id of the device we want to run code on

        :return list of tuples: A list of tuple from kind (<adapter_unique_name>, <device_raw_data>). The list is sorted
                             In a descending order of the best adapters to run code on. The device_raw_data is the raw
                             Data returned previously from the matching adapter.

        .. note:: We should still need to implement this function
        """
        result = self.request_remote_plugin(
            'online_device/{0}'.format(device_id), 'aggregator').json()

        try:
            for adapter_data in result['adapters']:
                adapter_name = adapter_data[PLUGIN_UNIQUE_NAME]
                # Currently adding all of the adapters
                # TODO: Create a smart logic here (next version)
                yield (adapter_name, adapter_data)
        except KeyError:
            return

    def request_remote_plugin_thread(self, action_id, plugin_unique_name, method, data):
        """ Function for request action from other adapter

        This function will run as a new thread. It will ask a request from other adapter.
        This function exists because we want to make the request without blocking the original request sent to us.

        :param str action_id: The id of the current action
        :param str plugin_unique_name: The plugin_unique_name of the adapter we want to execute action on
        :param str method: The method of the http request
        :param dict data: A dictionary conaining all the needed parameters for the current action request. For example, 
                          get_file request should have src_file parameter.
        """
        self.request_remote_plugin('action_update/{0}'.format(action_id),
                                   plugin_unique_name=plugin_unique_name,
                                   method='POST',
                                   data=data)

    def _reset_adapter_actions(self, unique_adapter_name):
        """ Function for reseting adapter's actions.
        This function will be called when an executing adapter was reset. In this case the Adapter dont know what 
        Actions he handled. This function will change the state of his open actions according to what we know. 
        For example, if the last state was 'started', then we cant know what is the current state and this action
        Will have a 'limbo' state.

        :param str unique_adapter_name: The unique name of the adapter that had reset.
        """
        # Finding all the actions related to this adapter
        collection = self._get_collection('actions')
        adapters_action = collection.find({'$and': [{'adapter_unique_name': unique_adapter_name},
                                                    {"status": {"$ne": "finished"}},
                                                    {"status": {"$ne": "failed"}},
                                                    {"status": {"$ne": "limbo"}}]})

        # Checking the status of each action, and changing status accordingly
        for one_action in adapters_action:
            if one_action['status'] == 'pending':
                self._save_action_data({'status': 'failed'})
            else:
                self._save_action_data({'status': 'limbo'})

    def ec_callback(self, action_id):
        """ A Callback for action updates

        This function is the regular Execution Controller callback for action updates sent by the adapters

        :param str action_id: The action id of the current update request issued this callback
        """
        # Checking if this is an action reset
        if action_id == 'adapter_action_reset':
            self._reset_adapter_actions(self.get_url_param('unique_name'))
            return

        request_content = self.get_request_data_as_object()

        # Updating the db on the new status and other parameters changed
        action_data = {'status': request_content['status']}
        if 'output' in request_content:
            action_data['product'] = request_content['output'].get('product', '')
            action_data['result'] = request_content['output'].get('result', '')

        self._save_action_data(action_data, action_id)

        if request_content['status'] == 'failed':
            # Should try another adapter, we will use the list of tuples containing all of the
            # available adapters for this device

            # Getting needed data to call the _create_request_thread again. It will handle the code execution
            # All over again.
            adapters_tuple = self._actions_db[action_id].get('adapters_tuple')
            action_type = self._actions_db[action_id]['action_type']
            device_id = self._actions_db[action_id]['device_id']
            issuer_unique_name = self._actions_db[action_id]['issuer_unique_name']
            data_for_action = self._actions_db[action_id]['data_for_action']
            current_adapter = self._actions_db[action_id]['adapter_unique_name']
            self.logger.warning('Adapter {0} failed to run action {1}'.format(
                current_adapter, action_id))
            if not adapters_tuple:
                self.logger.error(
                    'Couldnt run code on action {0}, no more adapters to try'.format(action_id))
            else:
                # Trying to run on a different adapter, don't need to inform the issuer
                self._actions_thread_pool.submit(self._create_request_thread,
                                                 action_type,
                                                 device_id,
                                                 issuer_unique_name,
                                                 data_for_action,
                                                 adapters_tuple,
                                                 action_id)
                return

        request_content['responder'] = self._actions_db[action_id].get('adapter_unique_name')

        # Updating the issuer plugin also
        to_request_params = {'action_id': action_id,
                             PLUGIN_UNIQUE_NAME: self._actions_db[action_id]['issuer_unique_name'],
                             'method': 'POST',
                             'data': json.dumps(request_content)}
        threading.Thread(target=self.request_remote_plugin_thread,
                         kwargs=to_request_params).start()

        return

    def _save_action_data(self, data_dict, action_id=None):
        """ Function for saving new action data.

        This function handles insertion of action, or update of existing action. It will save the data on the local
        Variable (_actions_db) and on our db.

        :param dict data_dict: A dictionary with the data to update. Only permitted keys will be updated on the local
                               Variable, but the db will update all of the keys shown on this dict.
        :param str action_id: The action_id of the action we want to update. If not present, the function will create
                              A new action.

        :return action_id: The action id of the action updated (or inserted if new)
        """
        available_data_keys = ['action_type', 'adapter_unique_name', 'issuer_unique_name', 'status', '_id',
                               'output', 'product', 'result', 'adapters_tuple', 'data_for_action', 'device_id',
                               'device_axon_id']

        # Adding the data to DB
        collection = self._get_collection('actions')
        if action_id:
            # Updating existing action (or creating new if this action id is not found)
            collection.update_one({'_id': ObjectId(action_id)}, update={
                                  '$set': data_dict}, upsert=True)
        else:
            # action_id is none, Creating a new doc
            insert_result = collection.insert_one(data_dict)
            action_id = str(insert_result.inserted_id)

        if action_id in self._actions_db:
            # This is an action update
            current_action_data = self._actions_db[action_id]
        else:
            # This is a new action
            current_action_data = dict()

        if data_dict.keys() - available_data_keys:
            self.logger.warning('Trying to add invalid key to action_data. '
                                'Keys: {0}'.format(data_dict.keys() - available_data_keys))
        current_action_data.update(
            {k: v for k, v in data_dict.items() if k in available_data_keys})

        self._actions_db[action_id] = current_action_data

        return action_id

    def _create_request_thread(self, action_type, device_id, issuer, data, adapters_tuple, action_id):
        """ A function for creating an action request

        This function should run as a new thread (since it could block for a while). It will try to request action from
        The first adapter from the adapters_tuple list. If the request fails, it will try the next on the list until
        Succeeded. 

        :param str action_type: The action type
        :param str device_id: The axon id of the device
        :param str issuer: The unique_plugin_name of the issuer plugin
        :param dict data: Extra data for the action
        :param list adapters_tuple: A list of tuples containing the adapters capable of running action on this device
        :param str action_id: The action id of this action thread
        """
        if not adapters_tuple:
            adapters_tuple = list(self._find_adapters_for_action(device_id))

        adapters_count = 1
        for adapter_unique_name, device_raw_data in adapters_tuple:
            # Requesting the adapter for the action
            result = self.request_action(action_type,
                                         self.ec_callback,
                                         data,
                                         adapter_unique_name,
                                         action_id,
                                         device_raw_data)

            if result.status_code == 200:
                # Action submitted successfully, Adding it to db
                self._save_action_data({'action_type': action_type,
                                        'data_for_action': data,
                                        'adapter_unique_name': adapter_unique_name,
                                        'device_id': device_id,
                                        'issuer_unique_name': issuer,
                                        'adapters_tuple': adapters_tuple[adapters_count:],
                                        'status': 'pending',
                                        'output': {}},
                                       action_id)
                self.request_remote_plugin('action_update/{0}'.format(action_id),
                                           plugin_unique_name=issuer,
                                           method='POST',
                                           data=json.dumps({'status': 'pending', 'output': ''}))
                return json.dumps({'action_id': action_id})
            self.logger.warning("Adapter failed running code on {id}. Reason: {mess}".format(id=device_id,
                                                                                             mess=result.content))
            adapters_count += 1
        self.request_remote_plugin('action_update/{0}'.format(action_id),
                                   plugin_unique_name=issuer,
                                   method='POST',
                                   data=json.dumps({'status': 'failed', 'output': ''}))
        self._save_action_data({'status': 'failed',
                                'product': 'No executing adapters'},
                               action_id)

    def request_action(self, action_type, callback_function, data_for_action,
                       plugin_unique_name, action_id, device_raw):
        """ A function for requesting action.

        This function will override the function implemented in PluginBase. The difference is that in this 
        function we are adding the action_id to the request from the remote plugin. and dont use other 
        unrelevant parameters

        :param str action_type: The type of the action. For example 'put_file'
        :param dict data_for_action: Extra data for executing the wanted action.
        :param func callback_function: A pointer to the callback function. This function will be called on each 
                                        update on this action id.
        :param str plugin_unique_name: The unique name of the plugin we want to send the request to. If not 
                                        presented, the request will be sent to the execution_controller plugin. 
        :param str action_id: Should hold the action id chosen by the EC to the Current action. 
        :param json device_raw: A json containing the raw data of the device. This data will help the executing 
                                adapter to run the action on the specific device.

        :return result: the result of the request (as returned from the REST request)
        """
        if data_for_action:
            data = data_for_action.copy()

        data['device_data'] = device_raw
        result = self.request_remote_plugin('action/' + action_type + '?action_id=' + action_id,
                                            plugin_unique_name=plugin_unique_name,
                                            method='POST',
                                            data=json.dumps(data))

        if not action_id:
            action_id = result.json()['action_id']

        self._open_actions[action_id] = callback_function

        return result

    @add_rule("action/<action_type>", methods=['POST'])
    def _make_action(self, action_type):
        """ Exported function for initiate new actions

        This function will start an action.
        url params:
            axon_id - The axon id of the device we want to initiate the action on
            issuer_name - The unique_plugin_name of the issuer plugin

        The data of the request should hold the extra parameters for the specific action.

        :param str action_type: The type of the action we want to run. For example: "put_file"
        """
        # Getting the wanted device axon_id
        device_id = self.get_url_param('axon_id')

        # Getting the issuer plugin unique name
        issuer_unique_name, _ = self.get_caller_plugin_name()

        # Getting the action parameters
        data_for_action = self.get_request_data_as_object()

        action_id = self._save_action_data({'action_type': action_type,
                                            'issuer_unique_name': issuer_unique_name,
                                            'status': 'pending',
                                            'device_axon_id': device_id})

        self._actions_thread_pool.submit(self._create_request_thread,
                                         action_type,
                                         device_id,
                                         issuer_unique_name,
                                         data_for_action,
                                         None,
                                         action_id)

        return jsonify({'action_id': action_id})
