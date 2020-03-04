import concurrent.futures
import logging
import time

from aws_adapter.connection.aws_connections import connect_client_by_source
from aws_adapter.connection.aws_ec2_eks_ecs_elb import query_devices_by_client_for_all_sources, \
    query_devices_by_client_by_source
from aws_adapter.connection.aws_generic_resources import get_account_metadata, query_aws_generic_region_resources
from aws_adapter.connection.aws_lambda import query_devices_by_client_by_source_lambda
from aws_adapter.connection.aws_nat import query_devices_by_client_by_source_nat
from aws_adapter.connection.aws_rds import query_devices_by_client_by_source_rds
from aws_adapter.connection.aws_route53 import query_devices_by_client_by_source_route53
from aws_adapter.connection.aws_s3 import query_devices_by_client_by_source_s3
from aws_adapter.connection.aws_ssm import query_devices_by_client_by_source_ssm
from aws_adapter.connection.aws_workspaces import query_devices_by_client_by_source_workspaces
from aws_adapter.connection.structures import AwsRawDataTypes
from axonius.clients.aws.aws_clients import get_boto3_session

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements, too-many-locals, too-many-lines
def query_devices_for_one_account(
        account,
        account_regions_clients,
        client_config: dict,
        https_proxy: str,
        account_i: int,
        num_of_accounts: int,
        options: dict
):
    successful_connections = []
    warnings_messages = []
    failed_connections = []
    try:
        logger.info(f'query_devices_by_client ({account_i} / {num_of_accounts}): {account}')
        account_start = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures_dict = {
                executor.submit(
                    connect_client_by_source, get_boto3_session(*client_data_by_region), region_name, client_config
                ): region_name for region_name, client_data_by_region in account_regions_clients.items()
            }

            connected_clients_by_region = dict()
            # Wait for all regions to connect
            for future in concurrent.futures.as_completed(futures_dict):
                region_name = futures_dict[future]
                current_try = f'{account}_{region_name}'
                try:
                    connected_clients, warnings = future.result()
                    connected_clients_by_region[region_name] = connected_clients
                    successful_connections.append(current_try)
                    if warnings:
                        error_string = f'{current_try}: Error while connecting to {",".join(warnings.keys())}.'
                        for service_name, service_error in warnings.items():
                            error_string += f'\n{service_name} - {service_error}'
                        logger.warning(error_string)
                        warnings_messages.append(error_string)
                except Exception as e:
                    logger.warning(f'problem with {current_try}', exc_info=True)
                    failed_connections.append(f'{current_try}: {str(e)}')

            # Now we have all clients connected for every region for this account. we start with getting info
            logger.info(f'Finished connecting')
            # that is interesting for all accounts.
            # this has to be non multi threaded because its api quota limited.
            if not connected_clients_by_region:
                return successful_connections, warnings_messages, failed_connections

            first_connected_client_region = 'us-east-1' if 'us-east-1' in connected_clients_by_region.keys() \
                else list(connected_clients_by_region.keys())[0]
            first_connected_client = connected_clients_by_region[first_connected_client_region]
            account_metadata = get_account_metadata(first_connected_client)
            parsed_data_for_all_regions = query_devices_by_client_for_all_sources(
                first_connected_client,
                options
            )

            logger.info(f'Finished querying account metadata and all-sources info')

            if options.get('fetch_route53') is True:
                logger.info(f'Fetching Route53 for {account}')
                source_name = f'{account}_Global'
                account_metadata['region'] = 'Global'
                try:
                    for parse_data_for_source in query_devices_by_client_by_source_route53(
                            first_connected_client):
                        yield source_name, \
                            account_metadata, \
                            parse_data_for_source, \
                            {}, \
                            AwsRawDataTypes.Route53
                except Exception:
                    logger.exception(f'Error while querying Route53')

            if options.get('fetch_s3') is True:
                logger.info(f'Fetching S3 for {account}')
                source_name = f'{account}_Global'
                account_metadata['region'] = 'Global'
                try:
                    for parse_data_for_source in query_devices_by_client_by_source_s3(first_connected_client):
                        yield source_name, \
                            account_metadata, \
                            parse_data_for_source, \
                            {}, \
                            AwsRawDataTypes.S3
                except Exception:
                    logger.exception(f'Error while querying S3')

            del first_connected_client

            # Get generic things
            futures_dict = {
                executor.submit(
                    query_aws_generic_region_resources, connected_client,
                ): region_name for region_name, connected_client in connected_clients_by_region.items()
            }

            generic_resources_by_region = dict()

            for future in concurrent.futures.as_completed(futures_dict):
                region_name = futures_dict[future]
                source_name = f'{account}_{region_name}'
                try:
                    generic_resources_by_region[region_name] = future.result()
                except Exception:
                    logger.exception(f'Error while querying generic resources in source {source_name}')

            logger.info(f'Starting to query devices for regions {",".join(connected_clients_by_region.keys())}')
            futures_dict = {
                executor.submit(
                    query_devices_by_client_by_source,
                    connected_client,
                    https_proxy,
                    options
                ): region_name for region_name, connected_client in connected_clients_by_region.items()
            }

            for future in concurrent.futures.as_completed(futures_dict):
                region_name = futures_dict[future]
                source_name = f'{account}_{region_name}'
                try:
                    parse_data_for_source = future.result()
                    parse_data_for_source.update(parsed_data_for_all_regions)
                    account_metadata['region'] = region_name

                    yield source_name, \
                        account_metadata, \
                        parse_data_for_source, \
                        generic_resources_by_region.get(region_name), \
                        AwsRawDataTypes.Regular

                    del parse_data_for_source
                except Exception:
                    logger.exception(f'Error while querying regular in source {source_name}')

            del parsed_data_for_all_regions
            del futures_dict

            if options.get('fetch_nat') is True:
                logger.info(f'Fetching NAT for {account}')
                for region_name, connected_clients in connected_clients_by_region.items():
                    source_name = f'{account}_{region_name}'
                    account_metadata['region'] = region_name
                    try:
                        for parse_data_for_source in query_devices_by_client_by_source_nat(connected_clients):
                            yield source_name, \
                                account_metadata, \
                                parse_data_for_source, \
                                generic_resources_by_region.get(region_name), \
                                AwsRawDataTypes.NAT
                    except Exception:
                        logger.exception(f'Error while querying NAT in source {source_name}')

            if options.get('fetch_lambda') is True:
                logger.info(f'Fetching Lambdas for {account}')
                for region_name, connected_clients in connected_clients_by_region.items():
                    source_name = f'{account}_{region_name}'
                    account_metadata['region'] = region_name
                    try:
                        for parse_data_for_source in query_devices_by_client_by_source_lambda(
                                connected_clients):
                            yield source_name, \
                                account_metadata, \
                                parse_data_for_source, \
                                generic_resources_by_region.get(region_name), \
                                AwsRawDataTypes.Lambda
                    except Exception:
                        logger.exception(f'Error while querying Lambda in source {source_name}')

            if options.get('fetch_workspaces') is True:
                logger.info(f'Fetching Workspaces for {account}')
                for region_name, connected_clients in connected_clients_by_region.items():
                    source_name = f'{account}_{region_name}'
                    account_metadata['region'] = region_name
                    try:
                        for parse_data_for_source in query_devices_by_client_by_source_workspaces(
                                connected_clients):
                            yield source_name, \
                                account_metadata, \
                                parse_data_for_source, \
                                generic_resources_by_region.get(region_name), \
                                AwsRawDataTypes.Workspaces
                    except Exception:
                        logger.exception(f'Error while querying workspaces in source {source_name}')

            if options.get('fetch_rds') is True:
                logger.info(f'Fetching RDS for {account}')
                for region_name, connected_clients in connected_clients_by_region.items():
                    source_name = f'{account}_{region_name}'
                    account_metadata['region'] = region_name
                    try:
                        for parse_data_for_source in query_devices_by_client_by_source_rds(connected_clients):
                            yield source_name, \
                                account_metadata, \
                                parse_data_for_source, \
                                generic_resources_by_region.get(region_name), \
                                AwsRawDataTypes.RDS
                    except Exception:
                        logger.exception(f'Error while querying rds in source {source_name}')

            if options.get('fetch_ssm') is True:
                logger.info(f'Fetching SSM for {account}')
                for region_name, connected_clients in connected_clients_by_region.items():
                    source_name = f'{account}_{region_name}'
                    account_metadata['region'] = region_name
                    try:
                        for parse_data_for_source in query_devices_by_client_by_source_ssm(connected_clients):
                            yield source_name, \
                                account_metadata, \
                                parse_data_for_source, \
                                generic_resources_by_region.get(region_name), \
                                AwsRawDataTypes.SSM
                    except Exception:
                        logger.exception(f'Error while querying SSM in source {source_name}')

            del connected_clients_by_region
        logger.info(f'query_devices_by_client ({account_i} / {num_of_accounts}): {account}'
                    f' ({round(time.time() - account_start, 2)} seconds)')
    except Exception:
        logger.exception(f'Problem querying from account {account}')
    return successful_connections, warnings_messages, failed_connections
