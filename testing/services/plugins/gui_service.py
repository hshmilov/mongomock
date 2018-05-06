import requests
import json
import os

from services.plugin_service import PluginService


class GuiService(PluginService):
    def __init__(self):
        super().__init__('gui')
        self._session = requests.Session()
        self.override_exposed_port = True

    @property
    def volumes_override(self):
        # GUI supports debug, but to use, you have to build your *local* node modules
        local_npm = os.path.join(self.service_dir, 'frontend', 'node_modules')
        local_dist = os.path.join(self.service_dir, 'frontend', 'dist')
        if os.path.isdir(local_npm) and os.path.isdir(local_dist):
            return super().volumes_override
        libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'axonius-libs', 'src', 'libs'))
        return [f'{libs}:/home/axonius/libs:ro']

    def get_dockerfile(self, mode=''):
        dev = '' if mode == 'prod' else 'dev-'
        return f"""
FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Compile npm
COPY ./frontend/package.json ./gui/frontend/package.json
# This must be the first thing so subsequent rebuilds will use this cache image layer
# (Docker builds the image from the dockerfile in stages [called layers], each layer is cached and reused if it should
#  not change [since the line created it + the layer before it has not changed]. So we moved the long process [of
#  npm install and the COPY of the package.json that it depends on] to be the first thing. if the file wont change
#  it would use the cached layer)
RUN cd ./gui/frontend && npm set progress=false && npm install

# Copy the current directory contents into the container at /app
COPY ./ ./gui/
COPY /config/nginx_conf.d/ /home/axonius/config/nginx_conf.d/

# Compile npm. we assume we have it from axonius-libs
RUN cd ./gui/frontend/ && npm run {dev}build
"""[1:]

    def __del__(self):
        self._session.close()

    def get_devices(self, *vargs, **kwargs):
        return self.get('device', session=self._session, *vargs, **kwargs)

    def get_devices_count(self, *vargs, **kwargs):
        return self.get('device/count', session=self._session, *vargs, **kwargs)

    def get_device_by_id(self, id, *vargs, **kwargs):
        return self.get('device/{0}'.format(id), session=self._session, *vargs, **kwargs)

    def get_all_tags(self, *vargs, **kwargs):
        return self.get('tags', session=self._session, *vargs, **kwargs)

    def remove_labels_from_device(self, payload, *vargs, **kwargs):
        return self.delete('device/labels', data=json.dumps(payload), session=self._session, *vargs,
                           **kwargs)

    def add_labels_to_device(self, payload, *vargs, **kwargs):
        return self.post('device/labels'.format(id), data=json.dumps(payload), session=self._session, *vargs, **kwargs)

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
