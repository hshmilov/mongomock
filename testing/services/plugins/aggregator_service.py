from retrying import retry

from services.plugin_service import API_KEY_HEADER, PluginService
import requests


class AggregatorService(PluginService):
    def __init__(self):
        super().__init__('aggregator')

    @retry(wait_random_min=2000, wait_random_max=7000, stop_max_delay=60 * 3 * 1000)
    def query_devices(self, adapter_id):
        response = requests.post(self.req_url + f"/trigger/{adapter_id}", headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, \
            f"Error in response: {str(response.status_code)}, " \
            f"{str(response.content)}"
        return response

    def add_label(self, name, unique_plugin_name, adapter_id, entity):
        # This code has to be the same as plugin_base.devices.add_label
        response = requests.post(
            self.req_url + "/plugin_push", headers={API_KEY_HEADER: self.api_key}, json={
                "association_type": "Tag",
                "associated_adapters": [
                    (unique_plugin_name, adapter_id)
                ],
                "name": name,
                "data": True,   # is enabled
                "type": "label",
                "entity": entity
            })
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def link(self, associated_adapters, entity):
        response = requests.post(
            self.req_url + "/plugin_push", headers={API_KEY_HEADER: self.api_key}, json={
                "association_type": "Link",
                "associated_adapters": associated_adapters,
                "entity": entity
            })
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def unlink(self, associated_adapters, entity):
        response = requests.post(
            self.req_url + "/plugin_push", headers={API_KEY_HEADER: self.api_key}, json={
                "association_type": "Unlink",
                "associated_adapters": associated_adapters,
                "entity": entity
            })
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def is_up(self):
        return super().is_up() and {"Triggerable"}.issubset(self.get_supported_features())
