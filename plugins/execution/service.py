import json
import logging
from datetime import datetime

from bson import json_util
from bson.objectid import ObjectId
from flask import jsonify
import pymongo

from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME, EXECUTION_PLUGIN_NAME
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.plugin_base import PluginBase, add_rule
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.utils.files import get_local_config_file
from axonius.utils.threading import run_and_forget

logger = logging.getLogger(f'axonius.{__name__}')

PLUGIN_TYPE = 'execution_controller'


class ExecutionService(PluginBase):
    """
    Plugin responsible for all the code execution on different devices
    """

    # Functions
    def __init__(self, **kwargs):
        # Initialize the base plugin (will initialize http server)
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=EXECUTION_PLUGIN_NAME, **kwargs)

        self.__actions_collection = self._get_collection('actions')
        self.__actions_collection.create_index([('status', pymongo.ASCENDING)], background=True)

        # Restore old actions list
        self._restore_actions_from_db()

        # Thread pool for creating new actions
        self._actions_thread_pool = LoggedThreadPoolExecutor(max_workers=20)

    def _restore_actions_from_db(self):
        """
        Restores actions from db.
        Will only restore actions that are not finished. If an action is on 'started' mode than it will become
        a 'limbo' action
        """
        # All actions that were pending before the plugin started haven't actually started
        # therefore they can be marked as failed actions
        self.__actions_collection.update_many(
            filter={
                'status': 'pending'
            },
            update={
                '$set': {
                    'status': 'failed'
                }
            }
        )

        self.__actions_collection.update_many(
            filter={
                'status': {
                    '$nin': ['finished', 'failed', 'limbo', 'pending']
                }
            },
            update={
                '$set': {
                    'status': 'failed'
                }
            }
        )

        all_actions = self.__actions_collection.find({
            'status': {
                '$nin': ['finished', 'failed', 'limbo']
            }
        })
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

    def _find_adapters_for_action(self, device_id, adapters_whitelist=None):
        """ This function should find the right adapters for executing actions

        The function will use the data saved on the devices db in order to find the best adapters for running code

        :param str device_id: The Axon id of the device we want to run code on
        :param list adapters_whitelist: a list of adapters whitelist, which are the only one we can execute code from.
        e.g., ['active_directory_adapter', 'esx_adapter']. If None, there is no whitelist.

        :return list of tuples: A list of tuple from kind (<adapter_unique_name>, <device_raw_data>). The list is sorted
                             In a descending order of the best adapters to run code on. The device_raw_data is the raw
                             Data returned previously from the matching adapter.

        .. note:: We should still need to implement this function
        """
        result = self.devices_db.find_one({'internal_axon_id': device_id})
        if result is None:
            logger.error('could not find device. Are you sure the device exists?')
            raise ValueError('could not find device. Are you sure the device exists?')
        try:
            for adapter_data in result['adapters']:
                adapter_name = adapter_data[PLUGIN_NAME]
                adapter_unique_name = adapter_data[PLUGIN_UNIQUE_NAME]
                if adapters_whitelist is None or adapter_name in adapters_whitelist:
                    yield (adapter_unique_name, adapter_data)
        except KeyError:
            return

    def request_remote_plugin_thread(self, action_id, plugin_unique_name, data):
        """
        Function for request action from other adapter

        This function will run as a new thread. It will ask a request from other adapter.
        This function exists because we want to make the request without blocking the original request sent to us.

        :param str action_id: The id of the current action
        :param str plugin_unique_name: The plugin_unique_name of the adapter we want to execute action on
        :param dict data: A dictionary containing all the needed parameters for the current action request. For example,
                          get_file request should have src_file parameter.
        """
        self.request_remote_plugin('action_update/{0}'.format(action_id),
                                   plugin_unique_name=plugin_unique_name,
                                   method='POST',
                                   data=data)

    def _reset_adapter_actions(self, unique_adapter_name):
        """
        Function for resetting adapter's actions.
        This function will be called when an executing adapter was reset. In this case the Adapter don't know what
        Actions he handled. This function will change the state of his open actions according to what we know.
        For example, if the last state was 'started', then we cant know what is the current state and this action
        Will have a 'limbo' state.

        :param str unique_adapter_name: The unique name of the adapter that had reset.
        """
        # Finding all the actions related to this adapter
        adapters_action = self.__actions_collection.find({
            '$and': [
                {
                    'adapter_unique_name': unique_adapter_name
                },
                {
                    'status': {
                        '$nin': ['finished', 'failed', 'limbo']
                    }
                }
            ]
        })

        # Checking the status of each action, and changing status accordingly
        for one_action in adapters_action:
            if one_action['status'] == 'pending':
                self._save_action_data({'status': 'failed'})
            else:
                self._save_action_data({'status': 'limbo'})

    def ec_callback(self, action_id):
        """
        A Callback for action updates

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

        action_data_status = action_data['status']
        action_data_result = action_data.get('resulpt')
        logger.info(f'Got action update on action {action_id}. status is {action_data_status},'
                    f'action result is {action_data_result}')

        self._save_action_data(action_data, action_id)

        current_action = self.__actions_collection.find_one({'_id': ObjectId(action_id)})
        accumulated_error = current_action.get('accumulated_error', '')

        if request_content['status'] == 'failed':
            # Should try another adapter, we will use the list of tuples containing all of the
            # available adapters for this device

            # Getting needed data to call the _create_request_thread again. It will handle the code execution
            # All over again.
            adapters_tuple = current_action.get('adapters_tuple')
            action_type = current_action['action_type']
            device_id = current_action['device_id']
            issuer_unique_name = current_action['issuer_unique_name']
            data_for_action = current_action['data_for_action']
            current_adapter = current_action['adapter_unique_name']

            # Add error to accumulated error
            current_adapter_failure = ''
            if 'output' in request_content:
                request_output = request_content['output']
                request_output_result = request_output.get('result')
                request_output_product = request_output.get('product')
                current_adapter_failure = f'result: {request_output_result}, ' \
                                          f'product: {request_output_product}'

            accumulated_error = accumulated_error + f'{current_adapter} failure: {current_adapter_failure}\n'

            logger.warning(f'Adapter {current_adapter} failed to run action {action_id}')
            if not adapters_tuple:
                logger.info(f'Couldn\'t run code on action {action_id}, no more adapters to try')
            else:
                # Trying to run on a different adapter, don't need to inform the issuer
                self._actions_thread_pool.submit(self._create_request_thread,
                                                 action_type,
                                                 device_id,
                                                 issuer_unique_name,
                                                 data_for_action,
                                                 adapters_tuple,
                                                 action_id,
                                                 accumulated_error)
                return

        request_content['responder'] = current_action.get('adapter_unique_name')
        request_content['accumulated_error'] = accumulated_error

        # Updating the issuer plugin also
        run_and_forget(lambda: self.request_remote_plugin_thread(action_id,
                                                                 current_action['issuer_unique_name'],
                                                                 json.dumps(request_content, default=json_util.default)
                                                                 ))

        return

    def _save_action_data(self, data_dict, action_id=None):
        """
        Function for saving new action data.

        This function handles insertion of action, or update of existing action.
        It will save the data on the collection.

        :param dict data_dict: A dictionary with the data to update. Only permitted keys will be updated on the local
                               variable, but the db will update all of the keys shown on this dict.
        :param str action_id: The action_id of the action we want to update. If not present, the function will create
                              a new action.

        :return action_id: The action id of the action updated (or inserted if new)
        """
        # Adding the data to DB
        if action_id:
            # Updating existing action (or creating new if this action id is not found)
            self.__actions_collection.update_one(filter={
                '_id': ObjectId(action_id)
            }, update={
                '$set': data_dict
            }, upsert=True)
        else:
            # action_id is none, Creating a new doc
            insert_result = self.__actions_collection.insert_one(data_dict)
            action_id = str(insert_result.inserted_id)

        return action_id

    def _create_request_thread(self, action_type, device_id, issuer, data, adapters_tuple, action_id,
                               accumulated_error, adapters_whitelist=None):
        """
        A function for creating an action request

        This function should run as a new thread (since it could block for a while). It will try to request action from
        The first adapter from the adapters_tuple list. If the request fails, it will try the next on the list until
        Succeeded.

        :param str action_type: The action type
        :param str device_id: The axon id of the device
        :param str issuer: The unique_plugin_name of the issuer plugin
        :param dict data: Extra data for the action
        :param list adapters_tuple: A list of tuples containing the adapters capable of running action on this device
        :param str action_id: The action id of this action thread
        :param str accumulated_error: since this function can be called numerous times, we store here the accumulated
                                      error for each time called.
        :param list adapters_whitelist: a whitelist of adapters from which we can execute code.
               e.g. ['active_directory_adapter'].
        """

        try:
            if not adapters_tuple:
                adapters_tuple = list(self._find_adapters_for_action(device_id, adapters_whitelist))

            adapters_count = 1
            for adapter_unique_name, device_raw_data in adapters_tuple:
                # Requesting the adapter for the action
                logger.debug(f'requesting {action_type} from {adapter_unique_name}, action id is {action_id}')
                result = self.__request_action(action_type,
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
                                            'accumulated_error': accumulated_error,
                                            'status': 'pending',
                                            'output': {}},
                                           action_id)
                    self.request_remote_plugin('action_update/{0}'.format(action_id),
                                               plugin_unique_name=issuer,
                                               method='POST',
                                               data=json.dumps({'status': 'pending', 'output': ''}))
                    return json.dumps({'action_id': action_id})

                if result.status_code != 501:
                    # Some general error happened, which is not 'Not Implemented'
                    logger.warning(f'Adapter failed running code on {device_id}. '
                                   f'Reason: {result.content}')

                    accumulated_error = accumulated_error + f'Failure from {adapter_unique_name}. ' \
                                                            f'Got status {result.status_code} with ' \
                                                            f'data {result.content}'
                adapters_count += 1

            if len(adapters_tuple) == 0:
                accumulated_error = 'Couldn\'t find any adapters to execute code with.'

            # Inform issuer.
            self.request_remote_plugin('action_update/{0}'.format(action_id),
                                       plugin_unique_name=issuer,
                                       method='POST',
                                       data=json.dumps({'status': 'failed', 'output': accumulated_error}))
            # Note! We search for 'no executing adapters' in other plugins... if you change it remember
            # to change it everywhere.
            self._save_action_data({'status': 'failed',
                                    'product': accumulated_error},
                                   action_id)
        except Exception as e:
            # Just update the status and raise it.
            self._save_action_data({'status': 'failed',
                                    'product': 'General error happened: {0}'.format(str(e))},
                                   action_id)
            # Inform issuer.
            self.request_remote_plugin('action_update/{0}'.format(action_id),
                                       plugin_unique_name=issuer,
                                       method='POST',
                                       data=json.dumps({'status': 'failed', 'output': str(e)}))
            raise
        return None

    def __request_action(self, action_type, callback_function, data_for_action, plugin_unique_name, action_id,
                         device_raw):
        """
        A function for requesting action.

        In this function we are adding the action_id to the request from the remote plugin.

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
        data = data_for_action.copy() if data_for_action else {}

        data['device_data'] = device_raw
        result = self.request_remote_plugin('action/' + action_type + '?action_id=' + action_id,
                                            plugin_unique_name=plugin_unique_name,
                                            method='POST',
                                            data=json.dumps(data, default=json_util.default))

        if not action_id:
            action_id = result.json()['action_id']

        with self._open_actions_lock:
            self._open_actions[action_id] = callback_function, datetime.now()

        return result

    @add_rule('action/<action_type>', methods=['POST'])
    def _make_action(self, action_type):
        """
        Exported function for initiate new actions

        This function will start an action.
        url params:
            axon_id - The axon id of the device we want to initiate the action on
            issuer_name - The unique_plugin_name of the issuer plugin

        The data of the request should hold the extra parameters for the specific action.

        :param str action_type: The type of the action we want to run. For example: 'put_file'
        """
        # Getting the wanted device axon_id
        device_id = self.get_url_param('axon_id')

        # Getting the issuer plugin unique name
        issuer_unique_name, _ = self.get_caller_plugin_name()

        # Getting the action parameters
        data_for_action = self.get_request_data_as_object()

        # Checkout if we have a whitelist of adapters. If we do have, remove it from the data_for_action
        # object, as it passes to the execution function.

        adapters_whitelist = data_for_action.pop('adapters_to_whitelist', None)
        if adapters_whitelist is not None:
            logger.info(f'Using adapters {adapters_whitelist}')

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
                                         action_id,
                                         '',
                                         adapters_whitelist=adapters_whitelist
                                         )

        return jsonify({'action_id': action_id})

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.Execution
