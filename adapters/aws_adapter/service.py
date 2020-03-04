import threading
import time
import logging
import re
import concurrent.futures
from collections import defaultdict
from typing import Optional

from aws_adapter.connection.aws_cis import append_aws_cis_data_to_device, append_aws_cis_data_to_user
from aws_adapter.connection.aws_connections import connect_client_by_source
from aws_adapter.connection.aws_devices import query_devices_for_one_account
from aws_adapter.connection.aws_ec2_eks_ecs_elb import parse_raw_data_inner_regular
from aws_adapter.connection.aws_generic_resources import get_account_metadata
from aws_adapter.connection.aws_nat import parse_raw_data_inner_nat
from aws_adapter.connection.aws_rds import parse_raw_data_inner_rds
from aws_adapter.connection.aws_route53 import parse_raw_data_inner_route53
from aws_adapter.connection.aws_s3 import parse_raw_data_inner_s3
from aws_adapter.connection.aws_ssm import parse_raw_data_inner_ssm
from aws_adapter.connection.aws_users import parse_raw_data_inner_users, query_users_by_client_for_all_sources
from aws_adapter.connection.aws_workspaces import parse_raw_data_inner_workspaces
from aws_adapter.connection.aws_lambda import parse_raw_data_inner_lambda
from aws_adapter.connection.structures import AWSUserAdapter, AWSDeviceAdapter, AWSAdapter, AwsRawDataTypes, \
    AWS_ACCESS_KEY_ID, AWS_ENDPOINT_FOR_REACHABILITY_TEST, REGION_NAME, GET_ALL_REGIONS, AWS_SECRET_ACCESS_KEY, \
    USE_ATTACHED_IAM_ROLE, ROLES_TO_ASSUME_LIST, PROXY, ACCOUNT_TAG
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.aws.aws_clients import get_boto3_session
from axonius.clients.aws.consts import GOV_REGION_NAMES, CHINA_REGION_NAMES, REGIONS_NAMES
from axonius.clients.aws.utils import get_aws_config
from axonius.clients.rest.connection import RESTConnection
from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable

logger = logging.getLogger(f'axonius.{__name__}')
DEFAULT_PARALLEL_COUNT = 5


'''
Matches AWS Instance IDs
'''
AWS_EC2_ID_MATCHER = re.compile('i-[0-9a-fA-F]{17}')


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements, too-many-locals
# pylint: disable=too-many-lines, too-many-instance-attributes, arguments-differ
class AwsAdapter(AdapterBase, Configurable):
    class MyUserAdapter(AWSUserAdapter):
        pass

    class MyDeviceAdapter(AWSDeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return (client_config.get(AWS_ACCESS_KEY_ID) or '') + (client_config.get(REGION_NAME) or GET_ALL_REGIONS)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(AWS_ENDPOINT_FOR_REACHABILITY_TEST)

    def _connect_client(self, original_client_config):
        # Credentials to some of the clients are temporary so we have to re-create them every cycle.
        # So here we must try to connect (if an exception occurs this will change the status of the adapter)
        # but this must occur every cycle.
        client_config = original_client_config.copy()

        has_iam_credentials = client_config.get(AWS_ACCESS_KEY_ID) and client_config.get(AWS_SECRET_ACCESS_KEY)
        has_attached_iam_instance_role = client_config.get(USE_ATTACHED_IAM_ROLE)

        if not has_iam_credentials and not has_attached_iam_instance_role:
            raise ClientConnectionException(f'Please specify credentials or select use attached instance role')

        if has_attached_iam_instance_role:
            # If the user requested to use the attached instance role, ignore the iam credentials.
            client_config.pop(AWS_ACCESS_KEY_ID, None)
            client_config.pop(AWS_SECRET_ACCESS_KEY, None)

        try:
            self._connect_client_once(client_config)
        except Exception as e:
            logger.exception(f'Error in connect_client')
            raise ClientConnectionException(str(e)[:500])
        return client_config

    def _connect_client_once(self, client_config):
        """
        Generates credentials and optionally tries to test them
        :param client_config: the configuration from the adapter scheme
        :return:
        """
        # We are going to change client_config throughout the function so copy it first
        clients_dict = dict()
        client_config = client_config.copy()

        # Lets start with getting all parameters and validating them.
        if client_config.get(ROLES_TO_ASSUME_LIST):
            roles_to_assume_file = self._grab_file_contents(client_config[ROLES_TO_ASSUME_LIST]).decode('utf-8')
        else:
            roles_to_assume_file = ''
        roles_to_assume_list = []

        # Input validation
        failed_arns = []
        pattern = re.compile('^arn:aws:iam::[0-9]+:role\/.*')   # pylint: disable=anomalous-backslash-in-string
        if roles_to_assume_file:
            for role_arn in roles_to_assume_file.strip().split(','):
                role_arn = role_arn.strip()
                # A role must look like 'arn:aws:iam::[account_id]:role/[name_of_role]
                # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html#genref-arns
                if not pattern.match(role_arn):
                    failed_arns.append(role_arn)
                roles_to_assume_list.append(role_arn)

        # Handle proxy settings
        https_proxy = client_config.get(PROXY)
        if https_proxy:
            logger.info(f'Setting proxy {https_proxy}')

        # Check if we have some failures
        if len(failed_arns) > 0:
            raise ClientConnectionException(
                f'Invalid role arns found. Please specify a comma-delimited list of valid role arns. '
                f'Invalid arns: {", ".join(failed_arns)}')

        if (client_config.get(GET_ALL_REGIONS) or False) is False:
            if not client_config.get(REGION_NAME):
                raise ClientConnectionException('No region was chosen')

            input_region_name = str(client_config.get(REGION_NAME)).lower()
            if input_region_name not in REGIONS_NAMES + GOV_REGION_NAMES + CHINA_REGION_NAMES:
                raise ClientConnectionException(f'region name {input_region_name} does not exist!')
            regions_to_pull_from = [input_region_name]
        else:
            regions_to_pull_from = REGIONS_NAMES + GOV_REGION_NAMES + CHINA_REGION_NAMES

        logger.info(f'Selected Regions: {regions_to_pull_from}')

        # We want to fail only if we failed connecting to everything we can. So what we do is we try to connect
        # and query the ec2 service which is mandatory for us.
        aws_access_key_id = client_config.get(AWS_ACCESS_KEY_ID) or 'attached iam role'
        clients_dict = defaultdict(dict)
        failed_connections = []
        successful_roles = set()
        ec2_check_status = dict()
        ec2_check_status_lock = threading.Lock()
        failed_connections_per_principal = defaultdict(set)

        def connect_iam(region_name: str):
            current_try = f'IAM User {aws_access_key_id} with region {region_name}'
            time_start = time.time()
            try:
                session_params = (
                    client_config.get(AWS_ACCESS_KEY_ID),
                    client_config.get(AWS_SECRET_ACCESS_KEY),
                    https_proxy,
                    region_name
                )
                permanent_session = get_boto3_session(*session_params)
                with ec2_check_status_lock:
                    # If ec2_check_status does not exist or is False, then we need to test ec2
                    should_test = not ec2_check_status.get(aws_access_key_id)
                if should_test:
                    self._test_ec2_connection(permanent_session, config=get_aws_config(client_config.get(PROXY)))
                clients_dict[aws_access_key_id][region_name] = session_params
                with ec2_check_status_lock:
                    ec2_check_status[aws_access_key_id] = True
            except Exception as e:
                failed_connections.append(f'{current_try}: {str(e)}')
                failed_connections_per_principal[aws_access_key_id].add(str(e))
            logger.debug(f'finished {current_try} after {round(time.time() - time_start, 2)} seconds')

        def connect_role(region_name: str, role_arn_inner: str):
            current_try = f'role {role_arn_inner} with region {region_name}'
            time_start = time.time()
            try:
                session_params = (
                    client_config.get(AWS_ACCESS_KEY_ID),
                    client_config.get(AWS_SECRET_ACCESS_KEY),
                    https_proxy,
                    region_name,
                    role_arn_inner
                )
                auto_refresh_session = get_boto3_session(*session_params)
                with ec2_check_status_lock:
                    # If ec2_check_status does not exist or is False, then we need to test ec2
                    should_test = not ec2_check_status.get(role_arn_inner)
                if should_test:
                    self._test_ec2_connection(auto_refresh_session, config=get_aws_config(client_config.get(PROXY)))
                clients_dict[role_arn_inner][region_name] = session_params
                with ec2_check_status_lock:
                    ec2_check_status[role_arn_inner] = True
                successful_roles.add(role_arn_inner)
            except Exception as e:
                failed_connections.append(f'{current_try}: {str(e)}')
                failed_connections_per_principal[role_arn_inner].add(str(e))
            logger.debug(f'finished {current_try} after {round(time.time() - time_start, 2)} seconds')

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # We assume the first region is going to succeed. So we are doing a small optimization here and try it out
            # first. If it is going to succeed, all the rest will not check for ec2 check (which takes time).
            # otherwise if it fails, they will all (in parallel) try to ec2-check it until one succeeds.

            # First, check Only IAM. If there is an error there we need to fail fast.
            logger.info(f'Checking {aws_access_key_id} connection..')
            connect_iam(regions_to_pull_from[0])
            futures_to_data = []
            for region in regions_to_pull_from[1:]:
                futures_to_data.append(executor.submit(connect_iam, region))
            for future_i, future in enumerate(concurrent.futures.as_completed(futures_to_data)):
                _ = future.result()

            if aws_access_key_id not in clients_dict:
                aws_access_key_id_errors = ','.join(
                    list(failed_connections_per_principal.get(aws_access_key_id) or set())
                )
                if 'aws was not able to validate the provided access credentials' in aws_access_key_id_errors.lower():
                    aws_access_key_id_errors = 'AWS was not able to validate the provided access credentials'

                logger.info(f'Error validating primary account: {aws_access_key_id_errors}')

                if self.__verify_primary_account:
                    raise ClientConnectionException(f'Error connecting to {aws_access_key_id}: '
                                                    f'{aws_access_key_id_errors}')

            # Next, check Roles
            logger.info(f'Checking {len(roles_to_assume_list)} roles..')
            # we do the same thing for roles as with iam users. Check the first region as an optimization
            futures_to_data = []
            for role_arn in roles_to_assume_list:
                futures_to_data.append(executor.submit(connect_role, regions_to_pull_from[0], role_arn))
            for future in concurrent.futures.as_completed(futures_to_data):
                _ = future.result()

            # Then, check all other regions
            futures_to_data = []
            for region in regions_to_pull_from[1:]:
                for role_arn in roles_to_assume_list:
                    futures_to_data.append(executor.submit(connect_role, region, role_arn))
            for future_i, future in enumerate(concurrent.futures.as_completed(futures_to_data)):
                _ = future.result()
                if future_i and future_i % 10 == 0:
                    logger.info(f'Finished instantiating {future_i} out of {len(futures_to_data)} aws connections')

        logger.info(f'Instantiation ended after {round(time.time() - start, 2)} seconds')

        failed_roles = set(roles_to_assume_list) ^ set(successful_roles)
        if failed_roles:
            logger.info(f'Failed roles ({len(failed_roles)} / {len(roles_to_assume_list)}): '
                        f'{failed_connections_per_principal}')
            if self.__verify_all_roles:
                failed_role_errors = ','.join(
                    list(failed_connections_per_principal.get(list(failed_roles)[0]) or set())
                )
                raise ClientConnectionException(f'Error assuming role: {list(failed_roles)[0]}: {failed_role_errors}')

        return clients_dict, client_config

    @staticmethod
    def _test_ec2_connection(session, **extra_params):
        try:
            boto3_client_ec2 = session.client('ec2', **extra_params)
            boto3_client_ec2.describe_instances(DryRun=True)
        except Exception as e:
            if 'Request would have succeeded, but DryRun flag is set.' not in str(e):
                raise

    def _query_devices_by_client(self, client_name, client_data_credentials):
        # we must re-create all credentials (const and temporary)
        https_proxy = client_data_credentials.get(PROXY)
        client_data, client_config = self._connect_client_once(client_data_credentials)
        # First, we must get clients for everything we need

        successful_connections = []
        failed_connections = []
        warnings_messages = []

        results = (yield from concurrent_multiprocess_yield(
            [
                (
                    query_devices_for_one_account,
                    (
                        account,
                        account_regions_clients,
                        client_config,
                        https_proxy,
                        account_i,
                        len(client_data.items()),
                        self.__options
                    ),
                    {}
                ) for account_i, (account, account_regions_clients) in enumerate(client_data.items())
            ],
            self.__parallel_count
        ))

        try:
            for result in results:
                if isinstance(result, tuple) and len(result) == 3:
                    successful_connections.extend(result[0])
                    warnings_messages.extend(result[1])
                    failed_connections.extend(result[2])
        except Exception:
            logger.exception(f'Failed parsing results from query_devices_for_one_account')

        total_connections = len(successful_connections) + len(failed_connections)
        content = ''
        if len(failed_connections) > 0:
            connections_failures = '\n\n'.join(failed_connections)
            content = f'Failed connections: \n{connections_failures}\n\n'
        if len(warnings_messages) > 0:
            warnings_str = '\n\n'.join(warnings_messages)
            content = f'Warnings: \n{warnings_str}'

        if self.__verbose_auth_notifications is True or len(successful_connections) == 0:
            self.create_notification(
                f'AWS Adapter (Devices): {len(successful_connections)} / {total_connections} successful connections, '
                f'{len(warnings_messages)} warnings.',
                content=content)

    def _query_users_by_client(self, client_name, client_data_credentials):
        # This is relevant just for IAM users, so we bail out if its not enabled.
        if not self.__fetch_iam_users:
            return

        # we must re-create all credentials (const and temporary)
        client_data, client_config = self._connect_client_once(client_data_credentials)
        # First, we must get clients for everything we need
        client_data_aws_clients = dict()
        successful_connections = []
        failed_connections = []
        warnings_messages = []
        for account, account_regions_clients in client_data.items():
            if account not in client_data_aws_clients:
                client_data_aws_clients[account] = dict()
            for region_name, client_data_by_region in account_regions_clients.items():
                current_try = f'{account}_{region_name}'
                try:
                    client_data_aws_clients[account][region_name], warnings = \
                        connect_client_by_source(
                            get_boto3_session(*client_data_by_region), region_name, client_config, 'users')
                    successful_connections.append(current_try)
                    if warnings:
                        for service_name, service_error in warnings.items():
                            error_string = f'{current_try}: {service_name} - {service_error}'
                            logger.warning(error_string)
                            warnings_messages.append(error_string)
                except Exception as e:
                    logger.warning(f'problem with {current_try}', exc_info=True)
                    failed_connections.append(f'{current_try}: {str(e)}')

        total_connections = len(successful_connections) + len(failed_connections)
        content = ''
        if len(failed_connections) > 0:
            connections_failures = '\n'.join(failed_connections)
            content = f'Failed connections: \n{connections_failures}\n\n'
        if len(warnings_messages) > 0:
            warnings_str = '\n'.join(warnings_messages)
            content = f'Warnings: \n{warnings_str}'

        if self.__verbose_auth_notifications is True or len(successful_connections) == 0:
            self.create_notification(
                f'AWS Adapter (Users): {len(successful_connections)} / {total_connections} successful connections, '
                f'{len(warnings_messages)} warnings.',
                content=content)

        for account, account_regions_clients in client_data_aws_clients.items():
            logger.info(f'query_users_by_client account: {account}')
            did_yield = None
            for region_name, client_data_by_region in account_regions_clients.items():
                source_name = f'{account}_{region_name}'
                try:
                    if not did_yield:
                        account_metadata = get_account_metadata(client_data_by_region)
                        account_metadata['region'] = region_name

                        for user_raw in query_users_by_client_for_all_sources(client_data_by_region):
                            yield source_name, account_metadata, user_raw, AwsRawDataTypes.Users
                        did_yield = True
                        break
                except Exception:
                    logger.exception(f'Problem querying source {source_name}')

    @staticmethod
    def _clients_schema():
        """
        The schema AWSAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': REGION_NAME,
                    'title': 'Region Name',
                    'type': 'string'
                },
                {
                    'name': GET_ALL_REGIONS,
                    'title': 'Get All Regions',
                    'type': 'bool'
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
                    'name': ACCOUNT_TAG,
                    'title': 'Account Tag',
                    'type': 'string'

                },
                {
                    'name': PROXY,
                    'title': 'Proxy',
                    'type': 'string'
                },
                {
                    'name': ROLES_TO_ASSUME_LIST,
                    'title': 'Roles to assume',
                    'description': 'A list of roles to assume',
                    'type': 'file'
                },
                {
                    'name': USE_ATTACHED_IAM_ROLE,
                    'title': 'Use attached IAM role',
                    'description': 'Use the IAM role attached to this instance instead of using the credentials',
                    'type': 'bool'
                }
            ],
            'required': [
                GET_ALL_REGIONS
            ],
            'type': 'array'
        }

    def __parse_raw_data(self, devices_raw_data):
        for aws_source, account_metadata, devices_raw_data_by_source, generic_resources, raw_data_type \
                in devices_raw_data:
            try:
                if raw_data_type == AwsRawDataTypes.Regular:
                    for device in parse_raw_data_inner_regular(
                            devices_raw_data_by_source,
                            generic_resources,
                            self._new_device_adapter,
                            self.__options
                    ):
                        if device:
                            self.append_metadata_to_entity(device, account_metadata, aws_source)
                            yield device
                elif raw_data_type == AwsRawDataTypes.SSM:
                    try:
                        device = parse_raw_data_inner_ssm(self._new_device_adapter(),
                                                          devices_raw_data_by_source,
                                                          generic_resources
                                                          )
                        if device:
                            self.append_metadata_to_entity(device, account_metadata, aws_source)
                            yield device
                    except Exception:
                        logger.exception(f'Problem parsing device from ssm')
                elif raw_data_type == AwsRawDataTypes.Lambda:
                    try:
                        device = parse_raw_data_inner_lambda(self._new_device_adapter(),
                                                             devices_raw_data_by_source,
                                                             generic_resources
                                                             )
                        if device:
                            self.append_metadata_to_entity(device, account_metadata, aws_source)
                            yield device
                    except Exception:
                        logger.exception(f'Problem parsing device from lambda')
                elif raw_data_type == AwsRawDataTypes.NAT:
                    try:
                        device = parse_raw_data_inner_nat(self._new_device_adapter(),
                                                          devices_raw_data_by_source,
                                                          generic_resources
                                                          )
                        if device:
                            self.append_metadata_to_entity(device, account_metadata, aws_source)
                            yield device
                    except Exception:
                        logger.exception(f'Problem parsing device from NAT')
                elif raw_data_type == AwsRawDataTypes.Route53:
                    try:
                        device = parse_raw_data_inner_route53(self._new_device_adapter(),
                                                              devices_raw_data_by_source,
                                                              generic_resources
                                                              )
                        if device:
                            self.append_metadata_to_entity(device, account_metadata, aws_source, {'region': 'Global'})
                            yield device
                    except Exception:
                        logger.exception(f'Problem parsing device from route53')
                elif raw_data_type == AwsRawDataTypes.S3:
                    try:
                        device = parse_raw_data_inner_s3(self._new_device_adapter(),
                                                         devices_raw_data_by_source,
                                                         generic_resources
                                                         )
                        if device:
                            self.append_metadata_to_entity(device, account_metadata, aws_source, {'region': 'Global'})
                            yield device
                    except Exception:
                        logger.exception(f'Problem parsing device from S3')
                elif raw_data_type == AwsRawDataTypes.RDS:
                    try:
                        device = parse_raw_data_inner_rds(self._new_device_adapter(),
                                                          devices_raw_data_by_source,
                                                          generic_resources
                                                          )
                        if device:
                            self.append_metadata_to_entity(device, account_metadata, aws_source)
                            yield device
                    except Exception:
                        logger.exception(f'Problem parsing device from RDS')
                elif raw_data_type == AwsRawDataTypes.Workspaces:
                    try:
                        device = parse_raw_data_inner_workspaces(self._new_device_adapter(),
                                                                 devices_raw_data_by_source,
                                                                 generic_resources
                                                                 )
                        if device:
                            self.append_metadata_to_entity(device, account_metadata, aws_source)
                            yield device
                    except Exception:
                        logger.exception(f'Problem parsing device from Workspaces')
                else:
                    logger.critical(f'Can not parse data for aws source {aws_source}, '
                                    f'unknown type {raw_data_type.name}')
            except Exception:
                logger.exception(f'Problem parsing data from source {aws_source}')

    def __parse_users_raw_data(self, users_raw_data):
        for aws_source, account_metadata, users_raw_data_by_source, raw_data_type in users_raw_data:
            try:
                if raw_data_type == AwsRawDataTypes.Users:
                    try:
                        user = parse_raw_data_inner_users(self._new_user_adapter(), users_raw_data_by_source)
                        if user:
                            self.append_metadata_to_entity(user, account_metadata, aws_source, {'region': 'Global'})
                            yield user
                    except Exception:
                        logger.exception(f'Problem parsing user')
                else:
                    logger.critical(f'Can not parse data for aws source {aws_source}, '
                                    f'unknown type {raw_data_type.name}')
            except Exception:
                logger.exception(f'Problem parsing data from source {aws_source}')

    @staticmethod
    def append_metadata_to_entity(
            entity: AWSAdapter,
            account_metadata: dict,
            aws_source: str,
            override_params: Optional[dict] = None
    ):
        try:
            account_aliases = account_metadata.get('aliases')
            if account_aliases and isinstance(account_aliases, list):
                entity.aws_account_alias = account_aliases
        except Exception:
            pass

        try:
            account_id = account_metadata.get('account_id')
            if account_id:
                entity.aws_account_id = str(account_id)
        except Exception:
            pass

        if override_params and 'region' in override_params:
            entity.aws_region = override_params['region']
        else:
            entity.aws_region = account_metadata.get('region')
        entity.account_tag = account_metadata.get('account_tag')
        entity.aws_source = aws_source

    def _parse_raw_data(self, *args, **kwargs):
        for device in self.__parse_raw_data(*args, **kwargs):
            try:
                device.aws_cis_incompliant = []     # delete old rules which might be irrelevant now
                if self.should_cloud_compliance_run():
                    append_aws_cis_data_to_device(device)
            except Exception as e:
                logger.debug(f'Failed adding cis device to data: {str(e)}')
            yield device

    def _parse_users_raw_data(self, *args, **kwargs):
        for user in self.__parse_users_raw_data(*args, **kwargs):
            try:
                user.aws_cis_incompliant = []       # delete old rules which might be irrelevant now
                if self.should_cloud_compliance_run():
                    append_aws_cis_data_to_user(user)
            except Exception:
                pass
            yield user

    def _on_config_update(self, config):
        logger.info(f'Loading AWS config: {config}')
        self.__options = config
        self.__correlate_ecs_ec2 = config.get('correlate_ecs_ec2') or False
        self.__correlate_eks_ec2 = config.get('correlate_eks_ec2') or False
        self.__fetch_instance_roles = config.get('fetch_instance_roles') or False
        self.__fetch_load_balancers = config.get('fetch_load_balancers') or False
        self.__fetch_rds = config.get('fetch_rds') or False
        self.__fetch_s3 = config.get('fetch_s3') or False
        self.__fetch_workspaces = config.get('fetch_workspaces') or False
        self.__fetch_lambda = config.get('fetch_lambda') or False
        self.__fetch_iam_users = config.get('fetch_iam_users') or False
        self.__fetch_ssm = config.get('fetch_ssm') or False
        self.__fetch_nat = config.get('fetch_nat') or False
        self.__fetch_route53 = config.get('fetch_route53') or False
        self.__parse_elb_ips = config.get('parse_elb_ips') or False
        self.__verbose_auth_notifications = config.get('verbose_auth_notifications') or False
        self.__shodan_key = config.get('shodan_key')
        self.__verify_all_roles = config.get('verify_all_roles') or False
        self.__verify_primary_account = config.get('verify_primary_account') or False
        self.__drop_turned_off_machines = config.get('drop_turned_off_machines') or False
        self.__parallel_count = config.get('parallel_count') or DEFAULT_PARALLEL_COUNT

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'correlate_ecs_ec2',
                    'title': 'Correlate ECS Containers with their EC2 Instance',
                    'type': 'bool'
                },
                {
                    'name': 'correlate_eks_ec2',
                    'title': 'Correlate EKS Containers with their EC2 Instance',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_instance_roles',
                    'title': 'Fetch information about EC2 attached roles',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_load_balancers',
                    'title': 'Fetch information about ELB (Elastic Load Balancers)',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_ssm',
                    'title': 'Fetch information about SSM (System Manager)',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_nat',
                    'title': 'Fetch information about NAT Gateways',
                    'type': 'bool'
                },
                {
                    'name': 'parse_elb_ips',
                    'title': 'Fetch ELB IP using current DNS',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_rds',
                    'title': 'Fetch information about RDS (Relational Database Service)',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_s3',
                    'title': 'Fetch information about S3',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_iam_users',
                    'title': 'Fetch information about IAM Users',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_workspaces',
                    'title': 'Fetch information about Workspaces',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_lambda',
                    'title': 'Fetch information about Lambdas',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_route53',
                    'title': 'Fetch information about Route 53',
                    'type': 'bool'
                },
                {
                    'name': 'verbose_auth_notifications',
                    'title': 'Show verbose notifications about connection failures',
                    'type': 'bool'
                },
                {
                    'name': 'shodan_key',
                    'title': 'Shodan API key for more IP info',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_all_roles',
                    'title': 'Verify all IAM roles',
                    'type': 'bool'
                },
                {
                    'name': 'verify_primary_account',
                    'title': 'Verify primary account permissions',
                    'type': 'bool'
                },
                {
                    'name': 'drop_turned_off_machines',
                    'title': 'Do not fetch EC2 machines that are turned off',
                    'type': 'bool'
                },
                {
                    'name': 'parallel_count',
                    'title': 'Num of accounts to fetch in parallel',
                    'type': 'integer'
                }
            ],
            'required': [
                'correlate_ecs_ec2',
                'correlate_eks_ec2',
                'fetch_instance_roles',
                'fetch_load_balancers',
                'fetch_rds',
                'fetch_s3',
                'fetch_iam_users',
                'fetch_workspaces',
                'fetch_lambda',
                'fetch_ssm',
                'fetch_nat',
                'fetch_route53',
                'parse_elb_ips',
                'verbose_auth_notifications',
                'verify_all_roles',
                'verify_primary_account',
                'drop_turned_off_machines',
                'parallel_count'
            ],
            'pretty_name': 'AWS Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'correlate_ecs_ec2': False,
            'correlate_eks_ec2': False,
            'fetch_instance_roles': False,
            'fetch_load_balancers': False,
            'fetch_rds': False,
            'fetch_s3': False,
            'fetch_iam_users': False,
            'fetch_workspaces': False,
            'fetch_lambda': False,
            'fetch_ssm': False,
            'fetch_nat': False,
            'fetch_route53': False,
            'parse_elb_ips': False,
            'verbose_auth_notifications': False,
            'shodan_key': None,
            'verify_all_roles': True,
            'verify_primary_account': True,
            'drop_turned_off_machines': False,
            'parallel_count': DEFAULT_PARALLEL_COUNT
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]
