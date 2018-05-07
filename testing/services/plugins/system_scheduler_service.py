import requests

from services.plugin_service import PluginService, API_KEY_HEADER


class SystemSchedulerService(PluginService):
    def __init__(self):
        super().__init__('system-scheduler')

    def stop_research(self):
        response = requests.post(
            self.req_url + "/stop_all", headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 204, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def start_research(self):
        response = requests.post(
            self.req_url + "/trigger/execute", headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def current_state(self):
        response = requests.get(
            self.req_url + "/state", headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response
