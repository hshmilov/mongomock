import json
import pytest

import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture
from bson.objectid import ObjectId


class ExecutionService(plugin_service.PluginService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../plugins/execution-plugin', **kwargs)

    def make_action(self, action_type, axon_id, data, adapters_to_whitelist=None):
        """
        Requests an action from the executer.
        :param action_type: The type of the action. e.g. "execute_shell"
        :param axon_id: the axon id of the device.
        :param data: the data. usually a json object with details about the action.
        :param adapters_to_whitelist: a list of strings, representing adapters which we want to run code from.
                e.g., ["ad_adapter"].
        :return: action_id.
        """

        action_url = f"action/{action_type}?axon_id={axon_id}"
        if adapters_to_whitelist is not None:
            data["adapters_to_whitelist"] = adapters_to_whitelist

        return self.post(action_url, api_key=self.api_key, data=data).json()["action_id"]

    def get_action_data(self, db, action_id=None):
        """
        Gets data about the action_id. if None, gets all actions.
        Currently we do this by querying the db.
        :param action_id: the action id.
        :return: a list of actions data.
        """

        if action_id is None:
            data = {}
        else:
            data = {"_id": ObjectId(action_id)}

        return list(db.get_collection(self.unique_name, "actions").find(data))


@pytest.fixture(scope="module")
def execution_fixture(request):
    service = ExecutionService()
    initialize_fixture(request, service)
    return service
