import requests
import json
import os

from services.plugin_service import PluginService


class GuiService(PluginService):
    def __init__(self):
        super().__init__('gui')
        self._session = requests.Session()

    @property
    def volumes_override(self):
        # GUI supports debug, but to use, you have to build your *local* node modules
        local_npm = os.path.join(self.service_dir, 'frontend', 'node_modules')
        local_dist = os.path.join(self.service_dir, 'frontend', 'dist')
        if os.path.isdir(local_npm) and os.path.isdir(local_dist):
            return super().volumes_override
        libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'plugins',
                                            'axonius-libs', 'src', 'libs'))
        return [f'{libs}:/home/axonius/libs:ro']

    def get_dockerfile(self, mode=''):
        dev = '' if mode == 'prod' else 'dev-'
        return f"""
FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY ./ ./gui/
COPY /config/nginx_conf.d/ /home/axonius/config/nginx_conf.d/

# Removing folders generated from build, so that next command will build properly
RUN cd ./gui/frontend && rm -rf dist node_modules

# Compile npm. we assume we have it from axonius-libs
RUN cd ./gui/frontend && npm set progress=false && npm install && npm run {dev}build"""[1:]

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

    def remove_labels_from_device(self, payload, *vargs, **kwargs):
        return self.delete('devices/labels', data=json.dumps(payload), session=self._session, *vargs,
                           **kwargs)

    def add_labels_to_device(self, payload, *vargs, **kwargs):
        return self.post('devices/labels'.format(id), data=json.dumps(payload), session=self._session, *vargs, **kwargs)

    def activate_plugin_job(self, plugin_id, *vargs, **kwargs):
        return self.post(f'plugins/{plugin_id}/start', *vargs, **kwargs)

    def deactivate_plugin_job(self, plugin_id, *vargs, **kwargs):
        return self.post(f'plugins/{plugin_id}/stop', *vargs, **kwargs)

    def get_queries(self):
        self.get('trigger_watches', api_key=self.api_key, session=self._session)

    def login_user(self, credentials):
        return self.post('login', data=json.dumps(credentials), session=self._session)

    def logout_user(self):
        return self.get('logout', session=self._session)
