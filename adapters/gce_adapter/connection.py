import logging
import time

from datetime import timedelta, datetime

import google.auth.crypt
import google.auth.jwt

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class GoogleCloudPlatformConnection(RESTConnection):
    def __init__(self, service_account_file: dict, *args, **kwargs):
        super().__init__(
            *args, domain='https://cloudresourcemanager.googleapis.com',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            **kwargs
        )
        self.__sa_file = service_account_file
        self.__access_token = None
        self.__last_token_fetch = None

    def _paginated_request(self, method, *args, **kwargs):
        self.refresh_token()
        resp = self._do_request(method, *args, **kwargs)
        yield resp
        while resp.get('nextPageToken'):
            url_params = kwargs.pop('url_params', None) or {}
            url_params['pageToken'] = resp.get('nextPageToken')
            kwargs['url_params'] = url_params
            self.refresh_token()
            resp = self._do_request(method, *args, **kwargs)
            yield resp

    def _paginated_get(self, *args, **kwargs):
        yield from self._paginated_request('GET', *args, **kwargs)

    def _paginated_post(self, *args, **kwargs):
        yield from self._paginated_request('POST', *args, **kwargs)

    def refresh_token(self, force: bool = False):
        if force or not self.__last_token_fetch or (self.__last_token_fetch + timedelta(minutes=50) < datetime.now()):
            now = int(time.time())
            sa_email = self.__sa_file['client_email']

            logger.debug(f'refreshing token')
            # build payload
            payload = {
                'iat': now,
                'exp': now + 3600,  # The maximum is one hour
                # iss must match 'issuer' in the security configuration in your
                # swagger spec (e.g. service account email). It can be any string.
                'iss': sa_email,
                'scope': 'https://www.googleapis.com/auth/cloudplatformprojects.readonly',
                # aud must be either your Endpoints service name, or match the value
                # specified as the 'x-google-audience' in the OpenAPI document.
                'aud':  'https://oauth2.googleapis.com/token',
                # sub and email should match the service account's email address
                'sub': sa_email,
                'email': sa_email
            }

            # sign with key file
            signer = google.auth.crypt.RSASigner.from_service_account_info(self.__sa_file)
            signed_jwt = google.auth.jwt.encode(signer, payload)

            response = self._post(
                'https://oauth2.googleapis.com/token',
                body_params='grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer'
                            '&assertion={}'.format(signed_jwt.decode('utf-8')),
                extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                use_json_in_body=False
            )

            if 'access_token' not in response:
                raise ValueError(f'Bad response: {response}')

            self._session_headers['Authorization'] = f'Bearer {response["access_token"]}'
            self.__last_token_fetch = datetime.now()

    def _connect(self):
        self.refresh_token(force=True)
        resp = self._get('v1/projects')
        if 'projects' not in resp:
            raise ValueError(f'Bad response while getting projects: {resp}')

    def get_project_list(self):
        for page in self._paginated_get('v1/projects'):
            if 'projects' not in page:
                raise ValueError(f'Bad response while getting projects: {page}')
            yield from page['projects']

    def get_device_list(self):
        pass

    def get_user_list(self, project_id: str):
        for page in self._paginated_post(f'v1/projects/{project_id}:getIamPolicy'):
            if 'bindings' not in page:
                raise ValueError(f'Bad response while getting iam policy for project {project_id}: {page}')
            yield from page['bindings']
