import logging

from google.cloud import bigquery   # pylint: disable=import-error, no-name-in-module
from google.oauth2 import service_account

from axonius.clients.rest.connection import RESTConnection


logger = logging.getLogger(f'axonius.{__name__}')


class GoogleBigQueryConnection(RESTConnection):
    """ rest client for GoogleBigQuery adapter """

    def __init__(self, service_account_file: bytes, project_id: str, dataset_id: str, *args, **kwargs):
        super().__init__(
            *args, url_base_prefix='',
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, **kwargs
        )

        self.__service_account_file = service_account_file
        self.__project_id = project_id
        self.__dataset_id = dataset_id
        self.__client = None

    def _connect(self):
        if not (self.__service_account_file and self.__project_id and self.__dataset_id):
            raise ValueError('Insufficient credentials!')

        credentials = service_account.Credentials.from_service_account_info(
            self.__service_account_file,
            scopes=['https://www.googleapis.com/auth/bigquery']
        )

        self.__client = bigquery.Client(
            credentials=credentials,
            project=self.__project_id
        )

        job = self.__client.query(
            f'select 1 from `{self.__project_id}.{self.__dataset_id}.ec2_instances` LIMIT 1'
        )
        job.cancel()

    def get_device_list(self):
        job = self.__client.query(
            f'SELECT * FROM `{self.__project_id}.{self.__dataset_id}.ec2_instances` '
            f'WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY) '
            f'AND scan_id = (SELECT MAX(scan_id) FROM `{self.__project_id}.{self.__dataset_id}.ec2_instances`)'
        )
        yield from job.result()
