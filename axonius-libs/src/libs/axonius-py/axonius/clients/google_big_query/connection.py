import logging

from typing import List, Dict, Tuple

from google.cloud import bigquery  # pylint: disable=import-error, no-name-in-module
from google.oauth2 import service_account
from google.cloud.bigquery.table import Table
from google.cloud.bigquery.schema import SchemaField
from google.cloud.exceptions import Conflict

from axonius.clients.google_big_query.consts import TYPE_TO_BIG_QUERY_TYPE
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

    def create_table(self, table_id: str, schema: Dict, data_to_write: List[Dict]) -> Tuple[bool, str]:
        try:
            big_query_schema = []
            for field, field_type in schema.items():
                if field_type not in TYPE_TO_BIG_QUERY_TYPE:
                    big_query_schema.append(SchemaField(field, 'STRING'))
                    for line in data_to_write:
                        if line.get(field) is None:
                            continue
                        line[field] = str(line[field])
                    continue
                big_query_schema.append(SchemaField(field, TYPE_TO_BIG_QUERY_TYPE[field_type]))

            table = Table(f'{self.__project_id}.{self.__dataset_id}.{table_id}',
                          schema=big_query_schema)
            try:
                table = self.__client.create_table(table)
                logger.info(f'Table was created {table_id}')
            except Conflict as e:  # The table already exists
                logger.warning(f'Table already exists {table_id}')

            errors = self.__client.insert_rows_json(table, data_to_write)
            if errors:
                return False, ','.join(errors)

            return True, 'Success'
        except Exception as e:
            logger.exception(f'Unable to create a table {table_id}, {schema}, {data_to_write}. Error: {str(e)}')
            return False, f'Unable to create a table {table_id}'
