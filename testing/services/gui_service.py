import requests
import json
import os

from services.plugin_service import PluginService
from test_credentials.test_gui_credentials import *


class GuiService(PluginService):
    def __init__(self):
        super().__init__('gui', service_dir='../plugins/gui')
        self._session = requests.Session()
        self.default_user = DEFAULT_USER

    @property
    def volumes_override(self):
        libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'plugins',
                                            'axonius-libs', 'src', 'libs'))
        return [f'{libs}:/home/axonius/libs:ro']

    def __del__(self):
        self._session.close()

    def get_devices(self, *vargs, **kwargs):
        return self.get('devices', session=self._session, *vargs, **kwargs)

    def get_devices_count(self, *vargs, **kwargs):
        return self.get('devices/count', session=self._session, *vargs, **kwargs)

    def get_device_by_id(self, id, *vargs, **kwargs):
        return self.get('devices/{0}'.format(id), session=self._session, *vargs, **kwargs)

    def get_all_tags(self, *vargs, **kwargs):
        return self.get('tags', session=self._session, *vargs, **kwargs)

    def remove_tags_from_device(self, payload, *vargs, **kwargs):
        return self.delete('devices/tags', data=json.dumps(payload), session=self._session, *vargs,
                           **kwargs)

    def add_tags_to_device(self, payload, *vargs, **kwargs):
        return self.post('devices/tags'.format(id), data=json.dumps(payload), session=self._session, *vargs, **kwargs)

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
