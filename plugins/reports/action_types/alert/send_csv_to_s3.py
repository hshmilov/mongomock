import datetime
import io
import logging

import boto3

from axonius.utils import gui_helpers
from axonius.utils.axonius_query_language import parse_filter
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert


logger = logging.getLogger(f'axonius.{__name__}')


class SendCsvToS3(ActionTypeAlert):
    """
    Send CSV results to defined share
    """
    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'access_key_id',
                    'title': 'IAM Access Key ID',
                    'type': 'string'
                },
                {
                    'name': 'secret_access_key',
                    'title': 'IAM Secret Access Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'use_attached_iam_role',
                    'title': 'Use attached IAM role',
                    'description': 'Use the IAM role attached to this instance instead of using the credentials',
                    'type': 'bool'
                },
                {
                    'name': 's3_bucket',
                    'title': 'S3 Bucket',
                    'type': 'string',
                }
            ],
            'required': [
                's3_bucket',
                'use_attached_iam_role',
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'access_key_id': None,
            'secret_access_key': None,
            's3_bucket': None,
            'use_attached_iam_role': False
        }

    def _run(self) -> AlertActionResult:
        try:
            query_name = self._run_configuration.view.name
            query = self._plugin_base.gui_dbs.entity_query_views_db_map[self._entity_type].find_one({
                'name': query_name
            })
            if query:
                parsed_query_filter = parse_filter(query['view']['query']['filter'])
                field_list = query['view'].get('fields', [])
                sort = gui_helpers.get_sort(query['view'])
            else:
                parsed_query_filter = self._create_query(self._internal_axon_ids)
                field_list = ['specific_data.data.name', 'specific_data.data.hostname',
                              'specific_data.data.os.type', 'specific_data.data.last_used_users']
                sort = {}
            csv_string = gui_helpers.get_csv(parsed_query_filter,
                                             sort,
                                             {field: 1 for field in field_list},
                                             self._entity_type)

            csv_data = io.BytesIO(csv_string.getvalue().encode('utf-8'))

            aws_access_key_id = None if self._config.get('use_attached_iam_role') else \
                self._config.get('access_key_id')
            aws_secret_access_key = None if self._config.get('use_attached_iam_role') else \
                self._config.get('secret_access_key')
            # Write to s3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            csv_name = 'axonius_csv_' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S').replace(' ', '-') + '.csv'
            bucket_name = self._config.get('s3_bucket')
            s3_client.put_object(ACL='bucket-owner-full-control', Bucket=bucket_name, Key=csv_name, Body=csv_data)

            return AlertActionResult(True, 'Wrote to S3')
        except Exception as e:
            logger.exception('Problem sending CSV to S3')
            exception_as_str = str(e)   # Done because of pylint error
            return AlertActionResult(False, f'Failed writing to S3: {exception_as_str}')
