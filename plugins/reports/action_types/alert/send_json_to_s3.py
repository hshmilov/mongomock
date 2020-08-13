import logging

from axonius.clients.aws.s3_client import S3Client
from axonius.utils import gui_helpers, db_querying_helper
from axonius.utils.json import to_json
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert
from reports.action_types.action_type_base import add_node_selection, \
    add_node_default
from reports.action_types.base.aws_utils import AWSActionUtils, \
    ACTION_CONFIG_USE_ADAPTER, ACTION_CONFIG_PARENT_TAG, \
    DEFAULT_S3_EC_OBJECT_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, \
    AWS_USE_IAM, AWS_S3_BUCKET_NAME, AWS_S3_KEY_NAME, ADAPTER_NAME, \
    AWS_REGION_NAME


logger = logging.getLogger(f'axonius.{__name__}')


class SendJsonToS3(ActionTypeAlert):
    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': ACTION_CONFIG_USE_ADAPTER,
                    'title': 'Use credentials from the AWS adapter',
                    'type': 'bool',
                },
                {
                    'name': AWS_ACCESS_KEY_ID,
                    'title': 'AWS Access Key ID',
                    'type': 'string'
                },
                {
                    'name': AWS_SECRET_ACCESS_KEY,
                    'title': 'AWS Secret Access Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': AWS_USE_IAM,
                    'title': 'Use attached IAM role',
                    'description': 'Use the IAM role attached to this instance instead of using the secret/access keys',
                    'type': 'bool',
                },
                {
                    'name': AWS_S3_BUCKET_NAME,
                    'title': 'Amazon S3 bucket name',
                    'type': 'string',
                },
                {
                    'name': AWS_S3_KEY_NAME,
                    'title': 'Amazon S3 object location (key)',
                    'type': 'string',
                },
                {
                    'name': 'append_datetime',
                    'title': 'Append date and time to file name',
                    'type': 'bool',
                },
                {
                    'name': 'overwrite_existing_file',
                    'title': 'Overwrite existing file',
                    'type': 'bool',
                }
            ],
            'required': [
                ACTION_CONFIG_USE_ADAPTER,
                AWS_ACCESS_KEY_ID,
                AWS_USE_IAM,
                AWS_S3_BUCKET_NAME,
                'append_datetime',
                'overwrite_existing_file'
            ],
            'type': 'array'
        }
        # enable the pop-up in the EC action for Core/Node
        return add_node_selection(config_schema=schema)

    @staticmethod
    def default_config() -> dict:
        default_config = AWSActionUtils.GENERAL_DEFAULT_CONFIG.copy()
        default_config.update({
            ACTION_CONFIG_USE_ADAPTER: False,
            AWS_ACCESS_KEY_ID: None,
            AWS_SECRET_ACCESS_KEY: None,
            AWS_USE_IAM: False,
            AWS_S3_BUCKET_NAME: None,
            AWS_S3_KEY_NAME: None,
            'append_datetime': False,
            'overwrite_existing_file': False
        })
        return add_node_default(default_config)

    # pylint: disable=protected-access, too-many-statements, no-else-return
    # pylint: disable=too-many-branches, invalid-triple-quote,
    # pylint: disable=too-many-return-statements
    def _run(self) -> AlertActionResult:
        """
        There are 2 flows here. The first flow uses the AWS adapter for
        the credentials (secret/access keys/instance role) and the other
        uses credentials that are input from within the EC action dialog.

        Shared data is first gathered, then the correct of the 2 flows is
        kicked off. Both flows will return and this method will return a
        AlertActionResult object that populates the Tasks area of the
        EC.

        :return: An AlertActionResult that contains Success or a Failure
        indicator and a short reason message.
        """
        try:
            # get the adapter name
            adapter_unique_name = self._plugin_base._get_adapter_unique_name(
                ADAPTER_NAME,
                self.action_node_id
            )
            if not isinstance(adapter_unique_name, str):
                raise ValueError(f'Malformed adapter name. Expected a string, '
                                 f'got {type(adapter_unique_name)}:'
                                 f'{str(adapter_unique_name)}')

            # get the parent tag, if this is a node and not a core
            parent_tag_name = self._config.get(ACTION_CONFIG_PARENT_TAG)
            if not isinstance(parent_tag_name, str) and parent_tag_name is not None:
                raise ValueError(f'Malformed parent tag name. Expected a string,'
                                 f' got {type(parent_tag_name)}')

            # leave if there is no data
            if not self._internal_axon_ids:
                return AlertActionResult(False, 'No Data')

            # get some default fields for the output file
            field_list = self.trigger_view_config.get('fields', [
                'specific_data.data.name',
                'specific_data.data.hostname',
                'specific_data.data.os.type',
                'specific_data.data.last_used_users',
                'labels'
            ])

            # get any column filters that might be in use
            field_filters = self.trigger_view_config.get('colFilters', {})

            # get all adapters that should be excluded from the action
            excluded_adapters = self.trigger_view_config.get('colExcludedAdapters', {})

            # get any sorting preferences from the gui
            sort = gui_helpers.get_sort(self.trigger_view_config)

            # set the name of the file to upload
            key_name = self._config.get(AWS_S3_KEY_NAME) or DEFAULT_S3_EC_OBJECT_KEY

            # get the data from the db
            entities = list(db_querying_helper.get_entities(
                limit=None,
                skip=None,
                view_filter=self.trigger_view_parsed_filter,
                sort=sort,
                projection={field: 1 for field in field_list},
                entity_type=self._entity_type,
                field_filters=field_filters,
                excluded_adapters=excluded_adapters))

            entities_json = to_json(entities or None)

            # this data is shared between use_adapter and EC action options
            data_dict = {
                'parent_tag_name': parent_tag_name,
                'account_id_for_upload': self._config.get(AWS_ACCESS_KEY_ID),
                'secret_key_for_upload': self._config.get(AWS_SECRET_ACCESS_KEY),
                'region_name': self._config.get(AWS_REGION_NAME),
                'bucket_name': self._config.get(AWS_S3_BUCKET_NAME),
                'key_name': key_name,
                'append_datetime': self._config.get('append_datetime'),
                'overwrite_existing_file': self._config.get(
                    'overwrite_existing_file') or False,
                'data': entities_json
            }

            # make the call to send_json_to_s3 in aws_adapter/service.py
            if self._config['use_adapter'] is True:
                logger.info(f'Started sending JSON to S3 (Adapter Mode)')
                try:
                    response = self._plugin_base.request_remote_plugin(
                        resource='send_json_to_s3',
                        plugin_unique_name=adapter_unique_name,
                        method='POST',
                        json=data_dict
                    )

                    if response is None:
                        raise ValueError(f'Failed communicating with adapter')

                    if response.status_code != 200:
                        return AlertActionResult(False, 'Failed to write to S3')

                except Exception as err:
                    logger.exception(f'Unable to connect to the AWS adapter: '
                                     f'{str(err)}')
                    raise

                logger.info(f'Finished sending JSON to S3 (Adapter Mode)')
                return AlertActionResult(True, 'Successful write to S3')

            # old skool, enter the creds in the EC and run normally
            else:
                logger.info(f'Started sending JSON to S3 (EC Mode)')
                try:
                    client = S3Client(
                        access_key=self._config.get(AWS_ACCESS_KEY_ID),
                        secret_key=self._config.get(AWS_SECRET_ACCESS_KEY),
                        use_instance_role=self._config.get(AWS_USE_IAM),
                        region=self._config.get(AWS_REGION_NAME)
                    )
                except Exception as err:
                    logger.exception(f'Unable to create S3 client: {str(err)}')
                    raise

                try:
                    if isinstance(client, S3Client):
                        client.send_data_to_s3(data=data_dict, data_type='json')
                        logger.info(f'Finished sending JSON to S3 (EC Mode)')
                        return AlertActionResult(True, 'Successful write to S3')
                    else:
                        logger.warning(f'Improperly created S3Client object. '
                                       f'Expected an S3Client, got a '
                                       f'{type(client)}: {str(client)}')
                        raise Exception(f'Unable to create the connection to '
                                        f'AWS. Please contact Axonius Support.')
                except Exception as err:
                    logger.exception(f'Unable to send data to S3: {str(err)}')
                    raise

        except Exception as err:
            logger.exception(f'Unable to upload Enforcement Center data to '
                             f'{self._config.get(AWS_ACCESS_KEY_ID)}')
            return AlertActionResult(False,
                                     f'Failed writing JSON to S3: {str(err)}')
