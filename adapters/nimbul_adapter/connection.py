import logging

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class NimbulConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json-rpc', 'Accept': 'application/json',
                                   'Authorization': f'Token token={self._apikey}'}

    def _connect(self):
        self._get('instances')

    def get_device_list(self):
        for device in self._get('instances'):
            yield 'instance', device

        for device in self._get('unmanaged_instances'):
            yield 'unmanaged', device

    def get_apps(self):
        apps_dict = dict()
        try:
            apps = self._get('apps')
            for app in apps:
                try:
                    if app.get('id'):
                        apps_dict[app.get('id')] = app
                except Exception:
                    logger.exception(f'Problem with app {app}')
            return apps_dict
        except Exception:
            logger.exception(f'Problem getting nimubl apps')
            return apps_dict

    def get_project(self):
        projects_dict = dict()
        try:
            projects = self._get('projects')
            for project in projects:
                try:
                    if project.get('cloud_id'):
                        projects_dict[project.get('cloud_id')] = project
                except Exception:
                    logger.exception(f'Problem with project {project}')
            return projects_dict
        except Exception:
            logger.exception(f'Problem getting nimubl projects')
            return projects_dict

    def get_user_list(self):
        for user in self._get('users'):
            yield 'user', user
