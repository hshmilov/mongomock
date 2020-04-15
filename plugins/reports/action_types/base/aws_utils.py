import re
import logging
import functools
from typing import Tuple, Optional, List, Generator, Iterable, Dict, Callable

import boto3
from boto3.resources.collection import ResourceCollection
from boto3.resources.base import ServiceResource
from botocore.config import Config
from botocore.credentials import RefreshableCredentials
from botocore.exceptions import ClientError, BotoCoreError
from botocore.session import get_session
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from axonius.types.enforcement_classes import EntityResult
from reports.action_types.action_type_base import add_node_default, generic_success, generic_fail

PROXY = 'proxy'
ADAPTER_NAME = 'aws_adapter'
AWS_USE_IAM = 'aws_use_iam'
AWS_ACCESS_KEY_ID = 'aws_access_key_id'
AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
AWS_ADAPTER_REQUIRED_FIELDS = {'cloud_id', 'aws_region', 'aws_source'}
AWS_ROLE_ARN_RE = re.compile('^arn:aws:iam::[0-9]+:role/.*')
EC2_ACTION_REQUIRED_ENTITIES = ['internal_axon_id', 'adapters.plugin_name', 'adapters.data.cloud_id',
                                'adapters.data.aws_device_type', 'adapters.data.aws_region',
                                'adapters.data.aws_source']
AWS_EC2_INSTANCE_STATES = {'pending', 'running', 'shutting-down', 'terminated', 'stopping', 'stopped'}
EC2_CONTAINER_DEVICE_TYPES = ['ECS', 'EKS']

logger = logging.getLogger(f'axonius.{__name__}')


@dataclass(frozen=True)
class EC2Instance(DataClassJsonMixin):
    id: str
    axon_id: str


@dataclass(frozen=True)
class EC2ActionResult(DataClassJsonMixin):
    instance_list: List[EC2Instance]
    reject_reason: Optional[str]


@dataclass(frozen=True)
class EC2InstanceGroup(DataClassJsonMixin):
    region: str
    role_arn: Optional[str]
    instance_list: List[EC2Instance]


EC2InstanceGroupIndex = Tuple[str, Optional[str]]
# Note: (PEP342) Yields EC2ActionResults and returns an optional "general error" affecting the rest action instances.
EC2ActionCallableReturnType = Generator[EC2ActionResult, None, Optional[str]]
EC2ActionCallable = Callable[[ServiceResource, EC2InstanceGroup], EC2ActionCallableReturnType]
EC2ActionCfgCallable = Callable[[ServiceResource, EC2InstanceGroup, Dict], EC2ActionCallableReturnType]


class AwsConnection():
    # Note: This code was mostly copied and adjusted from aws_adapter/service.py

    def __init__(self, client_config: dict):
        """
        Wraps AWS session generation for non-/role-assumed sessions
        :param client_config: Action configuration as given by the client (includes access keys, proxy settings etc)
        """
        self._client_config = client_config
        self._aws_config = self._init_aws_config(client_config)  # type: Optional[Config]

    @staticmethod
    def _init_aws_config(client_config: dict) -> Optional[Config]:
        https_proxy = client_config.get(PROXY)
        if https_proxy:
            logger.info(f'Setting proxy {https_proxy}')
            return Config(proxies={'https': https_proxy})
        return None

    def connect_ec2_resource(self, region_name: str, role_arn_inner: Optional[str] = None) -> ServiceResource:
        if role_arn_inner is None:
            session = self._generate_boto3_session(region_name)
        else:
            session = self._get_assumed_session(role_arn_inner, region_name)
        return session.resource('ec2', config=self._aws_config)

    def _generate_boto3_session(self, region_name: Optional[str] = None):
        use_iam = self._client_config[AWS_USE_IAM]
        access_key_id = None if use_iam else self._client_config.get(AWS_ACCESS_KEY_ID)
        secret_access_key = None if use_iam else self._client_config.get(AWS_SECRET_ACCESS_KEY)
        return boto3.Session(
            region_name=region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def _get_assumed_session(self, role_arn: str, region: str):
        """STS Role assume a boto3.Session

        With automatic credential renewal.
        Notes: We have to poke at botocore internals a few times
        """
        session_credentials = RefreshableCredentials.create_from_metadata(
            metadata=functools.partial(
                self._boto3_role_credentials_metadata_maker, role_arn)(),
            refresh_using=functools.partial(
                self._boto3_role_credentials_metadata_maker, role_arn),
            method='sts-assume-role'
        )
        role_session = get_session()
        # pylint: disable=W0212
        role_session._credentials = session_credentials
        role_session.set_config_variable('region', region)
        return boto3.Session(botocore_session=role_session)

    def _boto3_role_credentials_metadata_maker(self, role_arn: str):
        """
        Generates a "metadata" dict creator that is used to initialize auto-refreshing sessions.
        This is done to support auto-refreshing role-sessions; When we assume a role, we have to put a duration
        for it. when it expires, the internal botocore class will auto refresh it. This is the refresh function.
        for more information look at: https://dev.to/li_chastina/auto-refresh-aws-tokens-using-iam-role-and-boto3-2cjf
        :param role_arn: the name of the role to assume
        :return:
        """
        current_session = self._generate_boto3_session()
        sts_client = current_session.client('sts', config=self._aws_config)
        assumed_role_object = sts_client.assume_role(
            RoleArn=role_arn,
            DurationSeconds=60 * 15,  # The minimum possible, because we want to support any customer config
            RoleSessionName='Axonius'
        )

        response = assumed_role_object['Credentials']

        credentials = {
            'access_key': response.get('AccessKeyId'),
            'secret_key': response.get('SecretAccessKey'),
            'token': response.get('SessionToken'),
            'expiry_time': response.get('Expiration').isoformat(),
        }
        return credentials


class AWSActionUtils():

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': AWS_USE_IAM,
                    'title': 'Use attached IAM role',
                    'type': 'bool',
                    'default': False,
                },
                {
                    'name': AWS_ACCESS_KEY_ID,
                    'title': 'AWS Access Key ID',
                    'type': 'string'
                },
                {
                    'name': AWS_SECRET_ACCESS_KEY,
                    'title': 'AWS Access Key Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': PROXY,
                    'title': 'Proxy',
                    'type': 'string'
                },
            ],
            'required': [AWS_USE_IAM],
            'type': 'array'
        }
        return schema

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            AWS_USE_IAM: False,
            AWS_ACCESS_KEY_ID: None,
            AWS_SECRET_ACCESS_KEY: None,
            PROXY: None,
        })

    @staticmethod
    def perform_grouped_ec2_action(current_result: Iterable[dict], client_config: dict,
                                   action_func: EC2ActionCallable) -> Generator[EntityResult, None, None]:
        # Test valid configuration - either check use_iam boolean or use both cred fields
        if not (bool(client_config.get(AWS_USE_IAM)) ^
                bool(client_config.get(AWS_ACCESS_KEY_ID) and client_config.get(AWS_SECRET_ACCESS_KEY))):

            yield from generic_fail((entry['internal_axon_id'] for entry in current_result),
                                    'Either check "Use attached IAM role"'
                                    ' or fill both of "AWS Access Key ID" and "AWS Access Key Secret"')
            return

        # reject invalid entries (using PEP342) and group them into (region, role_arn) groups
        valid_entries = (yield from AWSActionUtils._reject_invalid_entries(current_result))
        instance_group_list = AWSActionUtils._group_ec2_devices_by_role_and_region(valid_entries)

        aws_connnection = AwsConnection(client_config)
        for instance_group in instance_group_list:

            action_results_iter = AWSActionUtils._connect_and_run_grouped_action_task(
                aws_connnection, action_func, instance_group)
            for result in AWSActionUtils._flush_results(instance_group, action_results_iter):
                if isinstance(result, Iterable):
                    yield from result
                else:
                    yield result

    @staticmethod
    def perform_grouped_ec2_cfg_action(
            current_result: Iterable[dict],
            client_config: dict,
            action_func: EC2ActionCfgCallable) -> Generator[EntityResult, None, None]:
        # Test valid configuration - both or none are valid
        if bool(client_config.get(AWS_ACCESS_KEY_ID)) ^ bool(client_config.get(AWS_SECRET_ACCESS_KEY)):
            yield from generic_fail((entry['internal_axon_id'] for entry in current_result),
                                    'Either both or none of "AWS Access Key ID" and "AWS Access Key Secret"'
                                    ' must be set')
            return

        # reject invalid entries (using PEP342) and group them into (region, role_arn) groups
        valid_entries = (yield from AWSActionUtils._reject_invalid_entries(current_result))
        instance_group_list = AWSActionUtils._group_ec2_devices_by_role_and_region(valid_entries)

        aws_connnection = AwsConnection(client_config)
        for instance_group in instance_group_list:

            action_results_iter = AWSActionUtils._connect_and_run_grouped_action_cfg_task(
                aws_connnection, action_func, instance_group, client_config)
            for result in AWSActionUtils._flush_results(instance_group, action_results_iter):
                if isinstance(result, Iterable):
                    yield from result
                else:
                    yield result

    @staticmethod
    def _group_ec2_devices_by_role_and_region(ec2_entry_list: Iterable[dict]):
        group_by_region_and_role = {}  # type: Dict[EC2InstanceGroupIndex, EC2InstanceGroup]

        for entry in ec2_entry_list:
            try:
                # Make sure entries are valid EC2 ones
                try:
                    aws_adapters_data = list(AWSActionUtils._iter_aws_adapters_data(entry, 'EC2'))
                    assert len(aws_adapters_data) == 1, 'Unsupported multiple EC2 Adapter connections'
                    aws_adapter_data = aws_adapters_data[0]
                except Exception:
                    logger.exception(f'Invalid EC2 entry retrieved for grouping: {entry}')
                    continue

                # extract region and optional role from
                region = aws_adapter_data.get('aws_region') or None
                if not region:
                    logger.error(f'Entry missing region: {entry}')
                    continue

                # retrieve role_arn, if was assumed through, from the aws_source
                role_arn = None  # type: Optional[str]
                entry_source = aws_adapter_data.get('aws_source') or None  # type: Optional[str]
                if entry_source:
                    # Note: aws_source format equals to '(role_arn / access_key)_region'
                    role_arn, region_from_source = entry_source.rsplit('_', 1)

                    # Make sure the split region matches the reported region.
                    # This is because '_' is a valid role character -
                    #   we must check that we didn't cut it by comparing source.
                    if region_from_source != region:
                        logger.warning(f'aws_source region part differs from region in entry: {entry}')
                        role_arn = None

                    # Make sure extracted role is valid, i.e. matches the role arn pattern
                    elif not AWS_ROLE_ARN_RE.match(role_arn):
                        role_arn = None
                else:
                    logger.warning(f'Entry missing source, assuming it was retrieved with no assumed-role: {entry}')

                group = group_by_region_and_role.setdefault(
                    (region, role_arn),
                    EC2InstanceGroup(region=region, role_arn=role_arn, instance_list=list()))

                group.instance_list.append(EC2Instance(id=aws_adapter_data['cloud_id'],
                                                       axon_id=entry['internal_axon_id']))
            except Exception:
                logger.exception(f'Unexpected error encountered for entry: {entry}')

        return list(group_by_region_and_role.values())

    @staticmethod
    def _connect_and_run_grouped_action_task(aws_connection: AwsConnection, action_func: EC2ActionCallable,
                                             instance_group: EC2InstanceGroup) -> EC2ActionCallableReturnType:

        region = instance_group.region
        role_arn = instance_group.role_arn

        try:
            # pylint: disable=C4001
            logger.debug(f'Connecting to EC2 on region "{region}"'
                         f'{f" using role {role_arn}" if role_arn else ""}.')
            ec2_resource = aws_connection.connect_ec2_resource(region_name=region, role_arn_inner=role_arn)
            return (yield from action_func(ec2_resource, instance_group))
        except BotoCoreError as e:
            logger.exception(f'Boto Error occurred during action on instances {instance_group.instance_list} ',
                             exc_info=e)
            return f'AWS Connection Error: {str(e)}'
        except ClientError as e:
            logger.exception(f'Error occurred during action on instances {instance_group.instance_list} ',
                             exc_info=e)
            # Return AWS Readable ErrorCode for easy error lookup
            return f'AWS Error: {e.response["Error"]["Code"]}'
        except Exception:
            logger.exception(f'Unhandled exception occurred during action on {instance_group}')
            return 'Unexpected error during action run'

    @staticmethod
    def _connect_and_run_grouped_action_cfg_task(
            aws_connection: AwsConnection,
            action_func: EC2ActionCfgCallable,
            instance_group: EC2InstanceGroup,
            client_config: dict) -> EC2ActionCallableReturnType:

        region = instance_group.region
        role_arn = instance_group.role_arn

        try:
            # pylint: disable=C4001
            logger.debug(f'Connecting to EC2 on region "{region}"'
                         f'{f" using role {role_arn}" if role_arn else ""}.')
            ec2_resource = aws_connection.connect_ec2_resource(region_name=region, role_arn_inner=role_arn)
            return (yield from action_func(ec2_resource, instance_group, client_config))
        except BotoCoreError as e:
            logger.exception(f'Boto Error occurred during action on instances {instance_group.instance_list} ',
                             exc_info=e)
            return f'AWS Connection Error: {str(e)}'
        except ClientError as e:
            logger.exception(f'Error occurred during action on instances {instance_group.instance_list} ',
                             exc_info=e)
            # Return AWS Readable ErrorCode for easy error lookup
            return f'AWS Error: {e.response["Error"]["Code"]}'
        except Exception:
            logger.exception(f'Unhandled exception occurred during action on {instance_group}')
            return 'Unexpected error during action run'

    @staticmethod
    def _flush_results(instance_group: EC2InstanceGroup, action_results_iter: EC2ActionCallableReturnType):

        # prepare resources for translation of EC2ActionResult to EntityResult
        instance_by_id_dict = {instance.id: instance for instance in instance_group.instance_list}

        def _convert_action_result_to_entity_result(action_result: EC2ActionResult) -> Iterable[EntityResult]:
            # translate instance id to axon id and pop it from the dict
            popped_instance_list = (instance_by_id_dict.pop(instance.id) for instance in
                                    action_result.instance_list)
            if action_result.reject_reason:
                return [AWSActionUtils._generic_fail_instance(instance, action_result.reject_reason)
                        for instance in popped_instance_list]
            return generic_success((inst.axon_id for inst in popped_instance_list))

        # forward (PEP342) translated results and fail rest if rest error was returned
        rest_error = (yield from map(_convert_action_result_to_entity_result, action_results_iter))
        if rest_error:
            logger.debug(f'Rest error "{rest_error}" is reported on {list(instance_by_id_dict.values())}')
            yield from (AWSActionUtils._generic_fail_instance(instance, rest_error)
                        for instance in instance_by_id_dict.values())

    @staticmethod
    def _reject_invalid_state_instances(ec2_resource: ServiceResource, instance_list: List[EC2Instance],
                                        instance_state_whitelist: List[str]) \
            -> Generator[EC2ActionResult, None, Optional[Tuple[ResourceCollection, List[EC2Instance]]]]:
        """
        Filter out instances of invalid state,
            see: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
        :param ec2_resource: EC2 authorized resource
        :param instance_list: EC2 Instance list to filter from
        :param instance_state_whitelist: whitelist of Instance state names
        :return: * (PEP342) yields EC2ActionResult
                 * None on failure or empty results
                 * tuple(ec2.instancesCollection, list(EC2Instance)) otherwise
        """

        instance_id_to_instance = {instance.id: instance for instance in instance_list}
        all_instance_ids = set(instance_id_to_instance.keys())
        valid_state_instances = AWSUtils.filter_instances_by_state(
            ec2_resource, all_instance_ids, whitelist=instance_state_whitelist)
        if valid_state_instances is None:
            yield EC2ActionResult(instance_list, 'AWS Instance Filtering Error')
            return None

        valid_instance_ids = {instance.id for instance in valid_state_instances}
        # Report back invalid state
        if len(valid_instance_ids) != len(all_instance_ids):
            yield EC2ActionResult(list(map(instance_id_to_instance.get, all_instance_ids - valid_instance_ids)),
                                  'AWS Instance Invalid State')
            if len(valid_instance_ids) == 0:
                logger.debug(f'Halting action due to no valid instances left after filter')
                return None

        return (valid_state_instances, list(map(instance_id_to_instance.get, valid_instance_ids)))

    @staticmethod
    def _reject_invalid_entries(entries_list: Iterable[dict]) -> Generator[EntityResult, None, List[dict]]:

        valid_entries = []  # type: List[dict]

        for entry in entries_list:
            reject_reason = AWSActionUtils._try_reject_entry(entry)
            if reject_reason:
                yield AWSActionUtils._generic_fail_axon(entry['internal_axon_id'], reject_reason)
            else:
                valid_entries.append(entry)

        return valid_entries

    #pylint: disable=R0911
    @staticmethod
    def _try_reject_entry(entry: dict) -> Optional[str]:
        try:
            # Retrieve Entry adapters list
            adapters_list = entry.get('adapters') or []
            if not adapters_list:
                return f'Missing adapters'

            # Filter out non AWS adapters
            aws_adapter_list = AWSActionUtils._iter_aws_adapters_data(entry)
            if not aws_adapter_list:
                return f'Missing AWS adapter'

            # Filter out non EC2 Adapter connections, make sure only a single one exists.
            ec2_adapter_list = list(AWSActionUtils._iter_aws_adapters_data(entry, 'EC2'))
            if len(ec2_adapter_list) == 0:
                return f'Missing AWS EC2 adapter connection.'
            if len(ec2_adapter_list) > 1:
                return f'Multiple AWS EC2 adapter connections encountered.'
            ec2_adapter_data = ec2_adapter_list[0]

            # Filter out device having ECS/EKS adapter connections, meaning they are containers over EC2.
            if any(next(AWSActionUtils._iter_aws_adapters_data(entry, unsupported_device_type), None)
                   for unsupported_device_type in EC2_CONTAINER_DEVICE_TYPES):
                return f'EC2 Devices running containers are currently unsupported.'

            # Filter out devices without required fields
            missing_fields = AWS_ADAPTER_REQUIRED_FIELDS - set(ec2_adapter_data.keys())
            if missing_fields:
                return f'Device missing required fields: {",".join(missing_fields)}'

            # Dont reject these
            return None

        except Exception:
            logger.exception(f'Unexpected error for entry {entry}.')
            return f'Unexpected error during entry validation check'

    @staticmethod
    def _generic_fail_instance_group(instance_group: EC2InstanceGroup, reject_reason: Optional[str] = None):
        return [AWSActionUtils._generic_fail_instance(instance, reject_reason)
                for instance in instance_group.instance_list]

    @staticmethod
    def _generic_fail_instance(instance: EC2Instance, reject_reason: Optional[str] = None):
        return AWSActionUtils._generic_fail_axon(instance.axon_id, reject_reason)

    @staticmethod
    def _generic_fail_axon(axon_id: str, reject_reason: Optional[str] = None):
        return EntityResult(axon_id, False, reject_reason)

    @staticmethod
    def _iter_aws_adapters_data(entry, device_type: Optional[str] = None):
        """ best effort extraction of the data part from aws_adapter connections """
        for adapter in (entry.get('adapters') or []):
            if (adapter.get('plugin_name') or '') != ADAPTER_NAME:
                continue
            adapter_data = adapter.get('data') or {}
            if device_type and ((adapter_data.get('aws_device_type') or '') != device_type):
                continue
            yield adapter_data


class AWSUtils():
    """
    boto3 operation wrappers
    """

    @staticmethod
    def filter_instances_by_state(ec2_resource: ServiceResource, instance_ids: Iterable[str],
                                  whitelist: List[str]) -> Optional[ResourceCollection]:
        # Note: boto3 does not accept set as a valid iterable,
        #       we transition non-list iterables into lists.
        whitelist = set(whitelist or [])
        validated_whitelist = list(AWS_EC2_INSTANCE_STATES.intersection(whitelist))
        if len(validated_whitelist) != len(whitelist):
            logger.warning(f'Ignoring unknown {whitelist - AWS_EC2_INSTANCE_STATES} whitelist values.'
                           f' Given whitelist: {whitelist},'
                           f' allowed list: {AWS_EC2_INSTANCE_STATES}.')

        try:
            return ec2_resource.instances.filter(InstanceIds=list(instance_ids),
                                                 Filters=[{
                                                     'Name': 'instance-state-name',
                                                     'Values': validated_whitelist,
                                                 }, ])
        except ClientError as e:
            logger.exception(f'Unexpected error occurred during instance retrieval and filtering'
                             f'for instances {",".join(instance_ids)} with whitelist {whitelist} ', exc_info=e)
            return None
