import pytest
import requests
import json
from services.plugin_service import PluginService
from test_credentials.test_gui_credentials import *


class GuiService(PluginService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../plugins/gui', **kwargs)
        self._session = requests.Session()
        self.default_user = DEFAULT_USER
        self.logged_in = False

    def __del__(self):
        self._session.close()

    def wait_for_service(self, interval=0.25, num_intervals=4 * 60 * 2):
        super().wait_for_service()
        self.login_default_user()
        self.logged_in = True

    def start_and_wait(self):
        super().start_and_wait()
        self.login_default_user()
        self.logged_in = True

    def stop(self, *vargs, **kwargs):
        if self.logged_in:
            self.logout_user()
            self.logged_in = False
        super().stop(*vargs, **kwargs)

    def get_devices(self, *vargs, **kwargs):
        return self.get('devices', session=self._session, *vargs, **kwargs)

    def get_devices_count(self, *vargs, **kwargs):
        return self.get('devices/count', session=self._session, *vargs, **kwargs)

    def get_device_by_id(self, id, *vargs, **kwargs):
        return self.get('devices/{0}'.format(id), session=self._session, *vargs, **kwargs)

    def get_all_tags(self, *vargs, **kwargs):
        return self.get('tags', session=self._session, *vargs, **kwargs)

    def remove_tags_from_device(self, id, tag_list, *vargs, **kwargs):
        return self.delete('devices/{0}/tags'.format(id), data=json.dumps(tag_list), session=self._session, *vargs,
                           **kwargs)

    def add_tags_to_device(self, id, tag_list, *vargs, **kwargs):
        return self.post('devices/{0}'.format(id), data=json.dumps(tag_list), session=self._session, *vargs, **kwargs)

    def activate_plugin_job(self, plugin_id, *vargs, **kwargs):
        return self.post(f'plugins/{plugin_id}/start', *vargs, **kwargs)

    def deactivate_plugin_job(self, plugin_id, *vargs, **kwargs):
        return self.post(f'plugins/{plugin_id}/stop', *vargs, **kwargs)

    def get_queries(self):
        self.get('trigger_watches', api_key=self.api_key, session=self._session)

    def login_default_user(self):
        resp = self.post('login', data=json.dumps(self.default_user), session=self._session)
        assert resp.status_code == 200
        return resp

    def login_user(self, credentials):
        return self.post('login', data=json.dumps(credentials), session=self._session)

    def logout_user(self):
        return self.get('logout', session=self._session)
