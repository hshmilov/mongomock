import pytest
from retrying import retry

from services.plugin_service import API_KEY_HEADER, PluginService
import requests


class AggregatorService(PluginService):
    def __init__(self, **kwargs):
        super().__init__('aggregator', service_dir='../plugins/aggregator-plugin', **kwargs)

    @retry(wait_fixed=3000,
           stop_max_delay=60 * 3 * 1000)
    def query_devices(self, adapter_id):
        response = requests.post(self.req_url + f"/trigger/{adapter_id}", headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, \
            f"Error in response: {str(response.status_code)}, " \
            f"{str(response.content)}"
        return response

    def add_tag(self, tagname, unique_plugin_name, adapter_id):
        response = requests.post(
            self.req_url + "/plugin_push", headers={API_KEY_HEADER: self.api_key}, json={
                "association_type": "Tag",
                "associated_adapter_devices": [
                    (unique_plugin_name, adapter_id)
                ],
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
                "association_type": "Unlink",
                "associated_adapter_devices": associated_adapter_devices,
            })
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def is_up(self):
        return super().is_up() and {"Activatable", "Triggerable"}.issubset(self.get_supported_features())
