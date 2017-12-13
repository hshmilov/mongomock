import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture
from services.plugin_service import API_KEY_HEADER
import requests


class AggregatorService(plugin_service.PluginService):
    def __init__(self, compose_file_path='../plugins/aggregator-plugin/docker-compose.yml',
                 config_file_path='../plugins/aggregator-plugin/src/plugin_config.ini',
                 container_name='aggregator'):
        super().__init__(compose_file_path, config_file_path, container_name)

    def query_devices(self):
        response = requests.post(
            self.req_url + "/query_devices", headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def add_tag(self, tagname, unique_plugin_name, adapter_id):
        response = requests.post(
            self.req_url + "/plugin_push", headers={API_KEY_HEADER: self.api_key}, json={
                "association_type": "Tag",
                "associated_adapter_devices": {
                    unique_plugin_name: adapter_id
                },
                "tagname": tagname,
                "tagvalue": tagname
            })
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def link(self, associated_adapter_devices):
        response = requests.post(
            self.req_url + "/plugin_push", headers={API_KEY_HEADER: self.api_key}, json={
                "association_type": "Link",
                "associated_adapter_devices": associated_adapter_devices,
            })
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def unlink(self, associated_adapter_devices):
        response = requests.post(
            self.req_url + "/plugin_push", headers={API_KEY_HEADER: self.api_key}, json={
                "association_type": "Unink",
                "associated_adapter_devices": associated_adapter_devices,
            })
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response


@pytest.fixture(scope="module")
def aggregator_fixture(request):
    service = AggregatorService()
    initialize_fixture(request, service)
    return service
