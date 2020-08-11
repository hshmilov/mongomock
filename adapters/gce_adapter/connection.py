import logging
import time
from collections import defaultdict

from datetime import timedelta, datetime

import google.auth.crypt
import google.auth.jwt

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')

CLOUD_SQL_BASE_URL = 'https://www.googleapis.com/sql/v1beta4/projects'
STORAGE_BASE_URL = 'https://www.googleapis.com/storage/v1'
BUCKETS_BASE_URL = f'{STORAGE_BASE_URL}/b'
IAM_BASE_URL = f'https://iam.googleapis.com'
SCC_BASE_URL = f'https://securitycenter.googleapis.com/v1'


class GoogleCloudPlatformConnection(RESTConnection):
    def __init__(self,
                 service_account_file: dict,
                 *args,
                 fetch_cloud_sql: bool = False,
                 fetch_storage: bool = False,
                 fetch_roles: bool = False,
                 scc_orgs: str = '',
                 **kwargs):
        super().__init__(
            *args, domain='https://cloudresourcemanager.googleapis.com',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            **kwargs
        )
        self.__sa_file = service_account_file
        self.__fetch_storage = fetch_storage
        self.__fetch_roles = fetch_roles
        self.__access_token = None
        self.__last_token_fetch = None
        self.__fetch_cloud_sql = fetch_cloud_sql
        if isinstance(scc_orgs, str):
            self.__scc_orgs = list(org.strip() for org in scc_orgs.split(','))
        elif isinstance(scc_orgs, list):
            self._scc_orgs = list(org.strip() for org in scc_orgs)
        self.__scopes = {
            'sql': ['https://www.googleapis.com/auth/sqlservice.admin'],
            'compute': ['https://www.googleapis.com/auth/cloudplatformprojects.readonly'],
            'storage': ['https://www.googleapis.com/auth/cloud-platform.read-only',
                        'https://www.googleapis.com/auth/devstorage.read_only'],
            'iam': ['https://www.googleapis.com/auth/cloud-platform.read-only',
                    'https://www.googleapis.com/auth/iam'],
            'scc': ['https://www.googleapis.com/auth/cloud-platform.read-only']
        }

    def _get_scopes(self):
        scopes = list()
        scopes.extend(self.__scopes['compute'])
        if self.__fetch_cloud_sql:
            scopes.extend(self.__scopes['sql'])
        if self.__fetch_storage:
            scopes.extend(self.__scopes['storage'])
        if self.__fetch_roles:
            scopes.extend(self.__scopes['iam'])
        if self.__scc_orgs:
            scopes.extend(self.__scopes['scc'])
        return ' '.join(scopes)

    def _paginated_request(self, method, *args, **kwargs):
        self.refresh_token()
        resp = self._do_request(method, *args, **kwargs)
        # logger.debug(f'Got response: {resp}')
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
                'scope': self._get_scopes(),
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

    def _get_sql_databases(self, project_id, instance_id):
        sql_db_url = f'{CLOUD_SQL_BASE_URL}/{project_id}/instances/{instance_id}/databases'
        # not actually paged!
        for page in self._paginated_get(sql_db_url, force_full_url=True):
            if 'items' not in page:
                raise ValueError(f'Bad response while getting cloud sql db databases: {page}')
            return page['items']

    def _get_sql_instances(self, project_id):
        sql_instances_url = f'{CLOUD_SQL_BASE_URL}/{project_id}/instances'
        for page in self._paginated_get(sql_instances_url, force_full_url=True):
            if 'items' not in page:
                raise ValueError(f'Bad response while getting cloud sql db instances: {page}')
            yield from page['items']

    def get_sql_instances(self, project_id):
        for sql_instance in self._get_sql_instances(project_id):
            sql_inst_id = sql_instance.get('masterInstanceName')
            if sql_inst_id:
                try:
                    sql_instance['databases'] = self._get_sql_databases(project_id, sql_inst_id)
                except Exception as e:
                    logger.warning(f'Got {str(e)} trying fetch databases for {sql_inst_id}')
                    sql_instance['databases'] = list()
            else:
                sql_instance['databases'] = list()
            yield sql_instance

    def _get_buckets_list(self, project_id: str, get_objects: bool = True):
        base_url = BUCKETS_BASE_URL

        for page in self._paginated_get(base_url, url_params={'project': project_id}, force_full_url=True):
            if 'items' not in page:
                if page == {'kind': 'storage#buckets'}:
                    logger.info(f'No buckets in project {project_id}')
                    continue
                raise ValueError(f'Bad response while getting buckets: {page}')
            for item in page['items']:
                item['projectId'] = project_id
                if get_objects:
                    try:
                        item['x_objects'] = list(self._get_bucket_objects(item['id']))
                    except Exception as e:
                        message = f'Failed to get objects for {item.get("id")}: {str(e)}'
                        logger.warning(message)
                        item['x_objects'] = []
                else:
                    item['x_objects'] = []
                yield item

    def _get_bucket_objects(self, bucket_id: str):
        bucket_url = f'{BUCKETS_BASE_URL}/{bucket_id}/o'
        for page in self._paginated_get(bucket_url, force_full_url=True):
            if 'items' not in page:
                if page == {'kind': 'storage#objects'}:
                    logger.debug(f'No objects in bucket {bucket_id}')
                    continue
                raise ValueError(f'Bad response while getting objects from bucket {bucket_id}: {page}')
            yield from page['items']

    def get_storage_list(self, get_bucket_objects=True, project_id=None):  # , paginated=False):
        """
        Get storage buckets for each project.
        If ``get_bucket_objects`` is set, then also get the objects for each bucket.
        :param get_bucket_objects: Optional. Set to True to get storage objects for each bucket.
        :param project_id: Optional. Get buckets only for this project_id (or a list of project_ids)
               By default, fetch buckets for all projects.
        :return: Yield dictionaries representing storage buckets.
        """
        if isinstance(project_id, list):
            projects = list([{'projectId': x} for x in project_id])
        else:
            projects = [{'projectId': project_id}, ] if project_id is not None else list(self.get_project_list())
        for i, project in enumerate(projects):
            project_id = project['projectId']
            logger.info(f'Storage: Handling project {i}/{len(projects)} - {project_id}')
            try:
                yield from self._get_buckets_list(project_id, get_objects=get_bucket_objects)
            except Exception as e:
                message = f'Failed to get buckets and info for project {project_id}: {str(e)}'
                if 'Unknown project id: 0' in str(e):
                    message = f'Failed to get buckets and info for project {project_id}. ' \
                              f'The project may have been deleted or the user may be unauthorized ' \
                              f'for this project.'
                    logger.warning(message)
                else:
                    logger.warning(message, exc_info=True)
                continue

    def get_databases(self, project_id=None):
        """
        Get Database (instances) for each project
        :param project_id: Optional. Get databases only for this project_id (or a list of project_ids)
            By defauilt, fetch databases for all projects.
        :return:  Yield dictionaries representing database instances
        """
        if isinstance(project_id, list):
            projects = list([{'projectId': x} for x in project_id])
        else:
            projects = [{'projectId': project_id}, ] if project_id is not None else list(self.get_project_list())
        for i, project in enumerate(projects):
            project_id = project['projectId']
            logger.info(f'Databases: Handling project {i}/{len(projects)} - {project_id}')
            try:
                # XXX Plug more database types HERE!
                if self.__fetch_cloud_sql:
                    yield from self.get_sql_instances(project_id)
                # XXX In future Add more database types
            except Exception as e:
                message = f'Failed to get database instances for project {project_id}: {str(e)}'
                if 'Unknown project id: 0' in str(e):
                    message = f'Failed to get database instances for project {project_id}. ' \
                              f'The project may have been deleted or the user may be unauthorized ' \
                              f'for this project.'
                    logger.warning(message, exc_info=False)
                else:
                    logger.exception(message)
                continue

    def get_device_list(self):
        pass

    def get_user_list(self, project_id: str):
        for page in self._paginated_post(f'v1/projects/{project_id}:getIamPolicy'):
            if 'bindings' not in page:
                raise ValueError(f'Bad response while getting iam policy for project {project_id}: {page}')
            yield from page['bindings']

    def get_predefined_roles(self):
        for page in self._paginated_get(f'{IAM_BASE_URL}/v1/roles', url_params={'view': 'FULL'}, force_full_url=True):
            if 'roles' not in page:
                raise ValueError(f'Bad response while getting predefined iam roles list: {page}')
            yield from page['roles']

    def get_project_roles(self, project_id: str):
        for page in self._paginated_get(f'{IAM_BASE_URL}/v1/projects/{project_id}/roles',
                                        url_params={'view': 'FULL'},
                                        force_full_url=True):
            if 'roles' not in page:
                raise ValueError(f'Bad response while getting iam roles list for project {project_id}: {page}')
            yield from page['roles']

    def _get_scc_sources(self, org_id):
        for page in self._paginated_get(f'{SCC_BASE_URL}/parent=organizations/{org_id}', force_full_url=True):
            if not (isinstance(page, dict) and isinstance(page.get('sources'), list)):
                raise ValueError(f'Bad response while getting scc sources list for organization {org_id}: {page}')
            yield from page['sources']

    def _get_scc_findings(self, org_id, source_id='-'):
        findings_url = f'{SCC_BASE_URL}/parent=organizations/{org_id}/sources/{source_id}/findings'
        for page in self._paginated_get(findings_url, force_full_url=True):
            if not (isinstance(page, dict) and isinstance(page.get('listFindingsResults'), list)):
                raise ValueError(f'Bad response while getting scc findings list for source {source_id}: {page}')
            yield from page['listFindingsResults']

    def _get_scc_assets(self, org_id):
        assets_url = f'{SCC_BASE_URL}/parent=organizations/{org_id}/assets'
        for page in self._paginated_get(assets_url, force_full_url=True):
            if not (isinstance(page, dict) and isinstance(page.get('listAssetResults'), list)):
                raise ValueError(f'Bad response while getting scc assets list for org {org_id}: {page}')
            yield from page['listAssetResults']

    @staticmethod
    def _map_findings_to_resources(findings_iter):
        """
        Create a resource_id: [finding, finding, ...] dict based on findings iterable
        :param findings_iter: Iterable of dictionaries, representing SCC findings.
        :return: dict[resource_name: list(findings)]
        """
        results_dict = defaultdict(list)
        for finding in findings_iter:
            if not isinstance(finding, dict):
                logger.warning(f'Failed to parse finding {finding}!')
                continue
            if not isinstance(finding.get('resource'), dict):
                logger.warning(f'Failed to get resource info from finding {finding}')
                continue
            res_name = finding.get('resource').get('name')
            if res_name and isinstance(res_name, str):
                results_dict[res_name].append(finding)
        return results_dict

    def get_scc_assets(self):
        for org in self.__scc_orgs:
            logger.info(f'Fetching scc assets and findings for org {org}')
            try:
                findings_iter = self._get_scc_findings(org)
                findings_dict = self._map_findings_to_resources(findings_iter)
                assets = self._get_scc_assets(org)
                for asset_result in assets:
                    if not isinstance(asset_result, dict):
                        logger.error(f'Asset result is not a dict: {asset_result}')
                        continue
                    asset = asset_result.get('asset')
                    if not isinstance(asset, dict):
                        logger.warning(f'Got bad asset {asset}, expected dict!')
                        continue
                    scc_props = asset.get('securityCenterProperties')
                    if not isinstance(scc_props, dict):
                        logger.warning(f'Got bad scc props for asset {asset}, '
                                       f'expected dict and got instead {scc_props}')
                        continue
                    resource_name = scc_props.get('resourceName')
                    asset['findings'] = findings_dict.get(resource_name)
                    asset['organization_id'] = org
                    yield asset
            except Exception as e:
                logger.warning(f'Got {str(e)} trying to get SCC assets and findings for org {org}', exc_info=True)
                continue
            logger.info(f'Finished fetching scc assets and findings for org {org}')
        logger.info(f'Finished fetching all scc assets and findings')
