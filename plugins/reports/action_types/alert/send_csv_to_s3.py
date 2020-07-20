import datetime
import io
import logging

import boto3

from axonius.clients.aws.utils import does_s3_key_exist
from axonius.utils import gui_helpers
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert


logger = logging.getLogger(f'axonius.{__name__}')

DEFAULT_S3_OBJECT_KEY = 'axonius_csv'


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
                    'title': 'IAM Access Key Id',
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
                    'title': 'Amazon S3 bucket name',
                    'type': 'string',
                },
                {
                    'name': 's3_key',
                    'title': 'Amazon S3 object location (key)',
                    'type': 'string',
                },
                {
                    'name': 'append_datetime',
                    'title': 'Append date and time to file name',
                    'type': 'bool',
                },
                {
                    'name': 'override_existing',
                    'title': 'Override file if exists',
                    'type': 'bool',
                }
            ],
            'required': [
                's3_bucket',
                'use_attached_iam_role',
                'append_datetime',
                'override_existing'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'access_key_id': None,
            'secret_access_key': None,
            's3_bucket': None,
            's3_key': DEFAULT_S3_OBJECT_KEY,
            'use_attached_iam_role': False,
            'append_datetime': True,
            'override_existing': True,
        }

    def _run(self) -> AlertActionResult:
        try:
            if not self._internal_axon_ids:
                return AlertActionResult(False, 'No Data')
            field_list = self.trigger_view_config.get('fields', [
                'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
                'specific_data.data.last_used_users', 'labels'
            ])
            field_filters = self.trigger_view_config.get('colFilters', {})
            excluded_adapters = self.trigger_view_config.get('colExcludedAdapters', {})
            sort = gui_helpers.get_sort(self.trigger_view_config)
            csv_string = gui_helpers.get_csv(self.trigger_view_parsed_filter,
                                             sort,
                                             {field: 1 for field in field_list},
                                             self._entity_type,
                                             field_filters=field_filters,
                                             excluded_adapters=excluded_adapters)

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
            csv_name = self._config['s3_key'] if self._config.get('s3_key') else DEFAULT_S3_OBJECT_KEY
            if self._config.get('append_datetime'):
                csv_name += '_' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S').replace(' ', '-')
            csv_name += '.csv'
            bucket_name = self._config.get('s3_bucket')
            if not self._config.get('override_existing'):
                # Do not override existing.
                if does_s3_key_exist(
                        bucket_name=bucket_name,
                        key_name=csv_name,
                        access_key_id=aws_access_key_id,
                        secret_access_key=aws_secret_access_key
                ):
                    raise ValueError(f'Key {csv_name} exists')
            s3_client.put_object(ACL='bucket-owner-full-control', Bucket=bucket_name, Key=csv_name, Body=csv_data)
            logger.info(f'Completed S3 csv file name: {csv_name}')
            return AlertActionResult(True, 'Wrote to S3')
        except Exception as e:
            logger.exception('Problem sending CSV to S3')
            exception_as_str = str(e)   # Done because of pylint error
            return AlertActionResult(False, f'Failed writing to S3: {exception_as_str}')
