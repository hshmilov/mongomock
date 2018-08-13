import functools
import time
import logging
from axonius.plugin_base import PluginBase, return_error, add_rule
from axonius.mixins.triggerable import Triggerable
from axonius.utils.files import get_local_config_file, get_random_uploaded_path_name
from axonius.utils.parsing import get_exception_string
from axonius.entities import AxoniusDevice

logger = logging.getLogger(f'axonius.{__name__}')

MAX_TRIES_FOR_EXECUTION_REQUEST = 3
SLEEP_BETWEEN_EXECUTION_TRIES_IN_SECONDS = 120


class DeviceControlService(PluginBase, Triggerable):
    def __init__(self, *args, **kargs):
        super().__init__(get_local_config_file(__file__), *args, **kargs)
        self._activate('execute')

    def _triggered(self, job_name: str, post_json: dict, *args):
        """
        Returns any errors as-is.
        :return:
        """
        if job_name != 'execute':
            logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)

        return ''

    @add_rule('run_action', methods=['POST'])
    def run_action(self):
        """
        Calls run_action_internal.
        :return:
        """
        if not self._execution_enabled:
            raise ValueError("Execution is disabled")
        return self.run_action_internal()

    def run_action_internal(self):
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

        :return:
        """
        request_content = self.get_request_data_as_object()
        try:
            internal_axon_ids = request_content['internal_axon_ids']    # a list of internal axon id's
            action_type = request_content['action_type']
            action_name = request_content['action_name']
            action_params = {}

            if action_type == 'shell':
                action_params['command'] = request_content['command']
            elif action_type == 'deploy':
                action_params['binary'] = request_content['binary']
                # Optional parameters
                action_params['params'] = request_content.get('params', '')
            else:
                raise ValueError(f"expected action type to be shell/deploy but got {action_type}")

            assert type(internal_axon_ids) == list
        except Exception:
            logger.exception("run_action: Incorrect parameters!")
            raise ValueError("run_action: Incorrect Parameters!")

        # Our steps:
        # 1. Get a list of these devices.
        # 2. Send an execution command. On Success, tag the devices. On failure, re-run until a
        #    certain limit is met.
        devices = []

        # Get a list of these devices. If a device is not found we raise an exception.
        # Getting an AxoniusDevice object is also an advantage since we are getting a representation
        # Of this device as adapter identities and not internal axon id which can change during correlation.
        for internal_axon_id in internal_axon_ids:
            device = list(self.devices.get(internal_axon_id=internal_axon_id))
            assert len(device) == 1, f"Internal axon id {internal_axon_id} was not found"
            devices.append(device[0])

        # Run the command.
        logger.info(f"Got {len(devices)} devices to run action {action_name} on. Sending commands..")
        for device in devices:
            # We might already have such action_name so clean the latest tags.
            device.add_label(f"Action '{action_name}' Error", False)
            device.add_label(f"Action '{action_name}' In Progress", False)
            device.add_label(f"Action '{action_name}' Success", False)
            device.add_label(f"Action '{action_name}' Failure", False)

            self.__request_action_from_device(device, action_name, action_type, action_params, 1)
            device.add_label(f"Action '{action_name}' In Progress")

        # This is not a synchronous functionality, so we are done.
        return "ok"

    def __request_action_from_device(self, device: AxoniusDevice, action_name, action_type,
                                     action_params, attempt_number, sleep_time=0):
        """
        Requests action from a device.
        :param device: an AxoniusDevice object.
        :param action_name: string representing the name of the action.
        :param action_type: string representing the type of the action.
        :param action_params: a dict representing the parameters for the action.
        :param attempt_number: an int representing what attempt is that.
        :param sleep_time: time to sleep before requesting, in seconds.
        :return: the execution promise.
        """

        time.sleep(sleep_time)

        if action_type == "shell":
            p = device.request_action(
                "execute_shell",
                {"shell_commands":
                 {os: [action_params['command']] for os in ["Windows", "Linux", "Mac", "iOS", "Android"]}}
            )
        elif action_type == "deploy":
            # we need to store the binary file.
            binary_arr = self._grab_file_contents(action_params['binary'])
            assert type(binary_arr) == bytes
            random_filepath = get_random_uploaded_path_name("device_control_deploy_binary")
            with open(random_filepath, "wb") as binary_file:
                binary_file.write(binary_arr)

            # We do not delete the file, assuming its small enough to just remain there and to be
            # there for further inspection if we need it.

            p = device.request_action(
                "execute_binary",
                {
                    "binary_file_path": random_filepath,
                    "binary_params": action_params['params']
                }
            )
        else:
            raise ValueError(f"expected action type to be shell/deploy but got {action_type}")

        p.then(did_fulfill=functools.partial(self.run_action_success, device, action_name,
                                             action_type, action_params, attempt_number),
               did_reject=functools.partial(self.run_action_failure, device, action_name,
                                            action_type, action_params, attempt_number))

        return p

    def run_action_success(self, device: AxoniusDevice, action_name, action_type,
                           action_params, attempt_number, data):
        """
        Success function for run shell.
        :param device: an AxoniusDevice object on which the command was run.
        :param action_name: the name of the action
        :param action_type: the type of the action
        :param action_params: the parameters of the action
        :param attempt_number: an int representing the current attempt number to run the command.
        :param data: the result of the execution.
        :return:
        """
        logger.info("got into run shell success.")
        try:
            output = data["output"]["product"][0]
            if output["status"] != "ok":
                # Its actually a failure!
                return self.run_action_failure(device, action_name, action_type, action_params, attempt_number,
                                               Exception(f"data status is not ok: {output}"))
        except Exception:
            logger.exception("Error in run shell success beginning")
            raise

        # Its a success
        try:
            logger.info(f"Success running action {action_name} "
                        f"on device {device.internal_axon_id} "
                        f"on attempt {attempt_number}")

            data_label = f"Acton type: {action_type}. "
            if action_type == "shell":
                data_label += f"Command: {action_params['command']}"
            elif action_type == "deploy":
                data_label += f"Binary file params: {action_params['params']}"

            data_label += f"\nResult:\n{output['data']}"
            device.add_data(f"Action '{action_name}'", data_label)
            device.add_label(f"Action '{action_name}' Success")
            device.add_label(f"Action '{action_name}' In Progress", False)

        except Exception:
            logger.exception(f"Exception in run_action_success")
            device.add_label(f"Action '{action_name}' Error")
            device.add_data(f"Action '{action_name}' Last Error", get_exception_string())

    def run_action_failure(self, device: AxoniusDevice, action_name, action_type,
                           action_params, attempt_number, exc):
        """
        Failure function for run shell.
        :param device: an AxoniusDevice object on which the command was run.
        :param action_name: the name of the action
        :param action_type: the type of the action
        :param action_params: the parameters of the action
        :param attempt_number: an int representing the current attempt number to run the command.
        :param exc: a string representing the error.
        :return:
        """
        logger.info(f"Got failure (attempt no {attempt_number}/{MAX_TRIES_FOR_EXECUTION_REQUEST}) for "
                    f"device {device.internal_axon_id}. retrying in {SLEEP_BETWEEN_EXECUTION_TRIES_IN_SECONDS}. "
                    f"exc is {str(exc)}")
        try:
            # Do not retry if the device is blacklisted
            if attempt_number >= MAX_TRIES_FOR_EXECUTION_REQUEST or "[BLACKLIST]" in str(exc):
                logger.error(f"Failed ({attempt_number}) with action {action_name}: "
                             f"attempts: {attempt_number}, exc: {exc}")
                device.add_data(f"Action '{action_name}' Last Error", str(exc))
                device.add_label(f"Action '{action_name}' Failure")
                device.add_label(f"Action '{action_name}' In Progress", False)
            else:
                # sleep and rerun
                self.execution_promises.submit(self.__request_action_from_device,
                                               device,
                                               action_name,
                                               action_type,
                                               action_params,
                                               attempt_number + 1,
                                               SLEEP_BETWEEN_EXECUTION_TRIES_IN_SECONDS)

        except Exception:
            logger.exception("Exception in run_action_failure")
            device.add_label(f"Action '{action_name}' Error")
            device.add_data(f"Action '{action_name}' Last Error", get_exception_string())

    @add_rule('test_run_action', methods=['POST'], should_authenticate=False)
    def test_run_action(self):
        """
        Just a wrapper to allow run_shell from tests
        :return:
        """
        return self.run_action_internal()
