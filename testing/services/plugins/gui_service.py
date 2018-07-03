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
    def exposed_ports(self):
        """
        :return: list of pairs (exposed_port, inner_port)
        """
        # The only container that listens to 80 and redirects to 80 is the gui, to allow http to https redirection.
        return [(80, 80)] + super().exposed_ports

    @property
    def volumes_override(self):
        # GUI supports debug, but to use, you have to build your *local* node modules
        local_npm = os.path.join(self.service_dir, 'frontend', 'node_modules')
        local_dist = os.path.join(self.service_dir, 'frontend', 'dist')
        if os.path.isdir(local_npm) and os.path.isdir(local_dist):
            return super().volumes_override
        libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'axonius-libs', 'src', 'libs'))
        volumes = [f'{libs}:/home/axonius/libs:ro']

        # extend volumes by mapping specifically each python file, to be able to debug much better.
        volumes.extend([f"{self.service_dir}/{fn}:/home/axonius/app/{self.package_name}/{fn}:ro"
                        for fn in os.listdir(self.service_dir) if fn.endswith(".py")])
        return volumes

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
        return self.get('devices', session=self._session, *vargs, **kwargs)

    def get_devices_count(self, *vargs, **kwargs):
        return self.get('devices/count', session=self._session, *vargs, **kwargs)

    def get_users_count(self, *vargs, **kwargs):
        return self.get('users/count', session=self._session, *vargs, **kwargs)

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

    def anaylitics(self):
        return self.get('analytics').content

    def troubleshooting(self):
        return self.get('troubleshooting').content

    def get_api_version(self, *vargs, **kwargs):
        return self.get(f'api', *vargs, **kwargs)

    def get_api_devices(self, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version()}/devices', *vargs, **kwargs)

    def get_api_device_by_id(self, device_id, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version()}/devices/{device_id}', *vargs, **kwargs)

    def get_api_users(self, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version().json()}/users', *vargs, **kwargs)

    def get_api_user_by_id(self, user_id, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version().json()}/users/{user_id}', *vargs, **kwargs)

    def get_api_reports(self, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version().json()}/reports', *vargs, **kwargs)

    def get_api_report_by_id(self, report_id, *vargs, **kwargs):
        return self.get(f'V{self.get_api_version().json()}/reports/{report_id}', *vargs, **kwargs)

    def delete_api_report_by_id(self, report_id, *vargs, **kwargs):
        return self.delete(f'V{self.get_api_version().json()}/reports/{report_id}', *vargs, **kwargs)

    def put_api_report(self, report_data, *vargs, **kwargs):
        return self.put(f'V{self.get_api_version().json()}/reports', report_data, *vargs, **kwargs)
