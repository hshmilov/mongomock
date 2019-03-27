import functools
import time
import logging
import traceback
from datetime import timedelta
from typing import Iterable, Tuple

from promise import Promise

from axonius.consts.plugin_consts import DEVICE_CONTROL_PLUGIN_NAME
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase, add_rule
from axonius.utils.files import get_local_config_file, get_random_uploaded_path_name
from axonius.utils.parsing import get_exception_string
from axonius.entities import AxoniusDevice

logger = logging.getLogger(f'axonius.{__name__}')

MAX_TRIES_FOR_EXECUTION_REQUEST = 3
SLEEP_BETWEEN_EXECUTION_TRIES_IN_SECONDS = 120


class DeviceControlService(Triggerable, PluginBase):
    def __init__(self, *args, **kargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=DEVICE_CONTROL_PLUGIN_NAME, *args, **kargs)

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name != 'execute':
            raise RuntimeError('Job name is wrong')

        promises = list(self.run_action_internal(post_json))
        promises_results = {}
        for p, internal_axon_id in promises:
            Promise.wait(p, timedelta(minutes=30).total_seconds())
            data = p.value

            if p.is_fulfilled:
                output = data['output']['product'][0]
                success = output['status'] == 'ok'
                promises_results[internal_axon_id] = {
                    'success': success,
                    'value': data
                }
            else:
                try:
                    logger.info(f'{data} is type {type(data)} {traceback.format_tb(data.__traceback__)}')
                    data = data.args[0]  # extract inner data from exception
                    product = data['output'].get('product')
                    if product and isinstance(product, BaseException):
                        data['output']['product'] = ''.join(traceback.format_tb(product.__traceback__))
                except Exception:
                    logger.info(f'Failed figuring out the error reason')

                promises_results[internal_axon_id] = {
                    'success': False,
                    'value': str(data)
                }

        return promises_results

    def run_action_internal(self, request_content) -> Iterable[Tuple[Promise, str]]:
        """
        Gets a list of devices and an action to do. Executes the action (currently shell command / binary)
        fails temporarily, reruns it.

        params - a json that contains:

        action_type - the action (str) to do. "shell", "binary"
        internal_axon_ids - list of internal axon ids (strings) that represent the devices to run on.
        action_name - the name (str) that we use to tag the devices with.

        in case the action is "shell":
            command - the command to run (str)

        in case the action is "deploy":
            binary - the actual binary to deploy and execute (will be removed after run)
            params - parameters to give the binary.

        :return: Iterator for tuples(Promise, internal_axon_id) - where the promise is for the execution on the
                    internal_axon_id given
        """
        try:
            internal_axon_ids = request_content['internal_axon_ids']    # a list of internal axon id's
            action_type = request_content['action_type']
            action_name = request_content['action_name']
            credentials = request_content.get('custom_credentials') or {}
            action_params = {}

            if action_type == 'shell':
                action_params['command'] = request_content['command']
            elif action_type == 'deploy':
                action_params['binary'] = request_content['binary']
                # Optional parameters
                action_params['params'] = request_content.get('params', '')
            else:
                raise ValueError(f'expected action type to be shell/deploy but got {action_type}')

            assert isinstance(internal_axon_ids, list)
        except Exception:
            logger.exception('run_action: Incorrect parameters!')
            raise ValueError('run_action: Incorrect Parameters!')

        # Our steps:
        # 1. Get a list of these devices.
        # 2. Send an execution command. On Success, tag the devices. On failure, re-run until a
        #    certain limit is met.
        devices = []

        # Get a list of these devices. If a device is not found we raise an exception.
        # Getting an AxoniusDevice object is also an advantage since we are getting a representation
        # Of this device as adapter identities and not internal axon id which can change during correlation.
        for internal_axon_id in internal_axon_ids:
            # Note that we are using the devices view which might not be updated. If a remote plugin tries
            # to run code we might not have this internal_axon_id in the devices view. But since right now
            # we are only using it from the gui (which shows the devices from the view that is okay until we
            # fix that bug).
            device = list(self.devices.get(internal_axon_id=internal_axon_id))
            assert len(device) == 1, f'Internal axon id {internal_axon_id} was not found'
            devices.append(device[0])

        # Run the command.
        logger.info(f'Got {len(devices)} devices to run action {action_name} on. Sending commands..')
        for device in devices:
            yield self.__request_action_from_device(device, action_name, action_type, action_params, credentials, 1), \
                device.internal_axon_id

    def __request_action_from_device(self, device: AxoniusDevice, action_name, action_type,
                                     action_params, credentials, attempt_number, sleep_time=0) -> Promise:
        """
        Requests action from a device.
        :param device: an AxoniusDevice object.
        :param action_name: string representing the name of the action.
        :param action_type: string representing the type of the action.
        :param action_params: a dict representing the parameters for the action.
        :param credentials: optional credentials
        :param attempt_number: an int representing what attempt is that.
        :param sleep_time: time to sleep before requesting, in seconds.
        :return: the execution promise.
        """

        time.sleep(sleep_time)

        if action_type == 'shell':
            p = device.request_action(
                'execute_shell',
                {
                    'shell_commands': {
                        os: [action_params['command']] for os in ['Windows', 'Linux', 'Mac', 'iOS', 'Android']
                    },
                    'custom_credentials': credentials
                }
            )
        elif action_type == 'deploy':
            # we need to store the binary file.
            binary_arr = self._grab_file_contents(action_params['binary'])
            assert isinstance(binary_arr, bytes)
            random_filepath = get_random_uploaded_path_name('device_control_deploy_binary')
            with open(random_filepath, 'wb') as binary_file:
                binary_file.write(binary_arr)

            # We do not delete the file, assuming its small enough to just remain there and to be
            # there for further inspection if we need it.

            p = device.request_action(
                'execute_binary',
                {
                    'binary_file_path': random_filepath,
                    'binary_params': action_params['params'],
                    'custom_credentials': credentials
                }
            )
        else:
            raise ValueError(f'expected action type to be shell/deploy but got {action_type}')

        p.then(did_fulfill=functools.partial(self.run_action_success, device, action_name,
                                             action_type, action_params, credentials, attempt_number),
               did_reject=functools.partial(self.run_action_failure, device, action_name,
                                            action_type, action_params, credentials, attempt_number))

        return p

    def run_action_success(self, device: AxoniusDevice, action_name, action_type,
                           action_params, credentials, attempt_number, data):
        """
        Success function for run shell.
        :param device: an AxoniusDevice object on which the command was run.
        :param action_name: the name of the action
        :param action_type: the type of the action
        :param action_params: the parameters of the action
        :param credentials: optional credentials
        :param attempt_number: an int representing the current attempt number to run the command.
        :param data: the result of the execution.
        :return:
        """
        logger.info('got into run shell success.')
        try:
            output = data['output']['product'][0]
            if output['status'] != 'ok':
                # Its actually a failure!
                return self.run_action_failure(
                    device, action_name, action_type, action_params, credentials, attempt_number,
                    Exception(f'data status is not ok: {output}')
                )
        except Exception:
            logger.exception('Error in run shell success beginning')
            raise

        # Its a success
        try:
            logger.info(f'Success running action {action_name} '
                        f'on device {device.internal_axon_id} '
                        f'on attempt {attempt_number}')

            data_label = f'Acton type: {action_type}. '
            if action_type == 'shell':
                command = action_params['command']
                data_label += f'Command: {command}'
            elif action_type == 'deploy':
                params = action_params['params']
                data_label += f'Binary file params: {params}'

            data = output['data']
            data_label += f'\nResult:\n{data}'
            device.add_data(f'Action \'{action_name}\'', data_label)

        except Exception:
            logger.exception(f'Exception in run_action_success')
            device.add_data(f'Action \'{action_name}\' Last Error', get_exception_string())

        return data

    def run_action_failure(self, device: AxoniusDevice, action_name, action_type,
                           action_params, credentials, attempt_number, exc):
        """
        Failure function for run shell.
        :param device: an AxoniusDevice object on which the command was run.
        :param action_name: the name of the action
        :param action_type: the type of the action
        :param action_params: the parameters of the action
        :param credentials: optional credentials
        :param attempt_number: an int representing the current attempt number to run the command.
        :param exc: a string representing the error.
        :return:
        """
        logger.info(f'Got failure (attempt no {attempt_number}/{MAX_TRIES_FOR_EXECUTION_REQUEST}) for '
                    f'device {device.internal_axon_id}. retrying in {SLEEP_BETWEEN_EXECUTION_TRIES_IN_SECONDS}. '
                    f'exc is {str(exc)}')
        try:
            if attempt_number >= MAX_TRIES_FOR_EXECUTION_REQUEST:
                logger.error(f'Failed ({attempt_number}) with action {action_name}: '
                             f'attempts: {attempt_number}, exc: {exc}')
                device.add_data(f'Action \'{action_name}\' Last Error', str(exc))
            else:
                # sleep and rerun
                self.execution_promises.submit(self.__request_action_from_device,
                                               device,
                                               action_name,
                                               action_type,
                                               action_params,
                                               credentials,
                                               attempt_number + 1,
                                               SLEEP_BETWEEN_EXECUTION_TRIES_IN_SECONDS)

        except Exception:
            logger.exception('Exception in run_action_failure')
            device.add_data(f'Action \'{action_name}\' Last Error', get_exception_string())

    @add_rule('test_run_action', methods=['POST'], should_authenticate=False)
    def test_run_action(self):
        """
        Just a wrapper to allow run_shell from tests
        :return:
        """
        list(self.run_action_internal(self.get_request_data_as_object()))
        return ''
