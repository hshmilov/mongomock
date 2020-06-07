import csv
import functools
import logging
import time
from enum import Enum, auto
from typing import Dict, Tuple

import boto3

from aws_adapter.connection.structures import AWSMFADevice, AWSIAMAccessKey, \
    AWSTagKeyValue, AWSIAMPolicy, AWSUserAdapter, AWSUserService, \
    AWSIAMPolicyPermission
from aws_adapter.connection.utils import get_paginated_marker_api, \
    create_custom_waiter, process_attached_iam_policy, process_inline_iam_policy
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


class AwsUserType(Enum):
    Regular = auto()
    Root = auto()


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-locals,
# pylint: disable=too-many-statements, logging-format-interpolation
def query_users_by_client_for_all_sources(client_data):
    iam_client = client_data.get('iam')
    if not iam_client:
        return None

    error_logs_triggered = []

    for users_page in get_paginated_marker_api(iam_client.list_users):
        for user in (users_page.get('Users') or []):
            username = user.get('UserName')
            if not username:
                continue

            try:
                groups = []
                user['group_attached_policies'] = list()
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_groups_for_user,
                                          UserName=username)
                ):
                    for group_raw in (page.get('Groups') or []):
                        group_name = group_raw.get('GroupName')
                        if group_name:
                            groups.append(group_name)

                            try:
                                logger.debug(f'Fetching group policy')
                                for agp_page in get_paginated_marker_api(
                                        functools.partial(
                                            iam_client.list_attached_group_policies,
                                            GroupName=group_name
                                        )
                                ):
                                    if not isinstance(agp_page, dict):
                                        raise ValueError(f'Malformed group '
                                                         f'policies page. '
                                                         f'Expected dict, got '
                                                         f'{type(agp_page)}: '
                                                         f'{str(agp_page)}')

                                    for attached_policy in (agp_page.get('AttachedPolicies') or []):
                                        if isinstance(attached_policy, dict):
                                            attached_policy = [attached_policy]

                                        if not isinstance(attached_policy, list):
                                            raise ValueError(
                                                f'Malformed attached policy. '
                                                f'Expected list, got '
                                                f'{type(attached_policy)}: '
                                                f'{str(attached_policy)}')

                                        for policy in attached_policy:
                                            if not isinstance(policy, dict):
                                                raise ValueError(f'Malformed policy.'
                                                                 f'Expected dict, got '
                                                                 f'{type(policy)}: '
                                                                 f'{str(policy)}')

                                            policy_name = policy.get('PolicyName')
                                            if not isinstance(policy_name, str):
                                                logger.warning(f'Malformed policy name. '
                                                               f'Expected str, got '
                                                               f'{type(policy_name)}: '
                                                               f'{str(policy_name)}')
                                                continue

                                            if policy_name == 'AdministratorAccess':
                                                user['has_administrator_access'] = True

                                            attached_group_policy = process_attached_iam_policy(
                                                iam_client=iam_client,
                                                attached_policy=policy)

                                            if not isinstance(attached_group_policy, dict):
                                                logger.warning(
                                                    f'Malformed attached user '
                                                    f'policy. Expected dict, got '
                                                    f'{type(attached_group_policy)}: '
                                                    f'{str(attached_group_policy)}')
                                                continue

                                            user['group_attached_policies'].append(
                                                attached_group_policy)

                            except Exception:
                                if 'list_attached_group_policies' not in error_logs_triggered:
                                    logger.exception(f'Problem with list_attached_group_policies')
                                    error_logs_triggered.append('list_attached_group_policies')

                    user['groups'] = groups

            except Exception:
                if 'list_groups_for_users' not in error_logs_triggered:
                    logger.exception(f'Problem with list_groups_for_user')
                    error_logs_triggered.append('list_groups_for_users')

            # user attached policies
            try:
                logger.debug(f'Fetching attached user policy')
                user['attached_policies'] = list()
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_attached_user_policies,
                                          UserName=username)
                ):
                    if not isinstance(page, dict):
                        raise ValueError(f'Malformed policy page. Expected '
                                         f'dict, got {type(page)}: '
                                         f'{str(page)}')

                    for attached_policies in (page.get('AttachedPolicies') or []):
                        # it's possible to get a dict or a list here
                        if isinstance(attached_policies, dict):
                            attached_policies = [attached_policies]

                        if not isinstance(attached_policies, list):
                            raise ValueError(f'Malformed attached policies. '
                                             f'Expected list, got '
                                             f'{type(attached_policies)}: '
                                             f'{str(attached_policies)}')

                        # get the policy name to check for AdministratorAccess
                        for policy in attached_policies:
                            if not isinstance(policy, dict):
                                raise ValueError(f'Malformed attached policy. '
                                                 f'Expected dict, got '
                                                 f'{type(policy)}: '
                                                 f'{str(policy)}')

                            policy_name = policy.get('PolicyName')
                            if not isinstance(policy_name, str):
                                logger.warning(f'Malformed policy name, '
                                               f'expected str, got '
                                               f'{type(policy_name)}: '
                                               f'{str(policy_name)}')
                                continue

                            if policy_name == 'AdministratorAccess':
                                user['has_administrator_access'] = True

                            attached_user_policy = process_attached_iam_policy(
                                iam_client=iam_client,
                                attached_policy=policy)

                            if not isinstance(attached_user_policy, dict):
                                logger.warning(f'Malformed user policy. '
                                               f'Expected dict, got '
                                               f'{type(attached_user_policy)}: '
                                               f'{str(attached_user_policy)}')
                                continue

                            user['attached_policies'].append(attached_user_policy)

            except Exception:
                if 'list_attached_user_policies' not in error_logs_triggered:
                    logger.exception(f'Problem with list_attached_user_policies')
                    error_logs_triggered.append('list_attached_user_policies')

            # user inline policies
            try:
                logger.debug(f'Fetching inline user policy')
                user['inline_policies'] = list()
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_user_policies,
                                          UserName=username)
                ):
                    if not isinstance(page, dict):
                        raise ValueError(f'Malformed inline policy page, '
                                         f'expected a dict, got '
                                         f'{type(page)}: {str(page)}')

                    for inline_policy in page.get('PolicyNames') or []:
                        if not isinstance(inline_policy, str):
                            raise ValueError(f'Malformed inline policies. '
                                             f'Expected str, got '
                                             f'{type(inline_policy)}: '
                                             f'{str(inline_policy)}')

                        if inline_policy == 'AdministratorAccess':
                            user['has_administrator_access'] = True

                        inline_user_policy = process_inline_iam_policy(
                            client=iam_client,
                            user_name=username,
                            policy=inline_policy)

                        if not isinstance(inline_user_policy, dict):
                            logger.warning(f'Malformed inline user policy. '
                                           f'Expected dict, got '
                                           f'{type(inline_user_policy)}: '
                                           f'{str(inline_user_policy)}')

                        user['inline_policies'].append(inline_user_policy)

            except Exception:
                if 'list_user_policies' not in error_logs_triggered:
                    logger.exception(f'Problem with list_user_policies')
                    error_logs_triggered.append('list_user_policies')

            try:
                access_keys = []
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_access_keys,
                                          UserName=username)
                ):
                    for access_key_metadata in page.get('AccessKeyMetadata') or []:
                        access_key_id = access_key_metadata.get('AccessKeyId')
                        if access_key_id:
                            try:
                                response = iam_client.get_access_key_last_used(
                                    AccessKeyId=access_key_id)
                                access_key_metadata['AccessKeyLastUsed'] = response['AccessKeyLastUsed']
                            except Exception:
                                pass
                            access_keys.append(access_key_metadata)

                user['access_keys'] = access_keys
            except Exception:
                if 'list_access_keys' not in error_logs_triggered:
                    logger.exception(f'Problem with list_access_keys')
                    error_logs_triggered.append('list_access_keys')

            try:
                response = iam_client.get_login_profile(UserName=username)
                # If there is no login profile, it means password is not assigned, only access keys.
                if response:
                    user['user_is_password_enabled'] = True
            except Exception:
                pass

            try:
                user['mfa_devices'] = []
                for mfa_devices_page in get_paginated_marker_api(
                        functools.partial(iam_client.list_mfa_devices,
                                          UserName=username)
                ):
                    user['mfa_devices'].extend(mfa_devices_page.get('MFADevices') or [])
            except Exception:
                if 'list_mfa_devices' not in error_logs_triggered:
                    logger.exception(f'Problem with list_mfa_devices')
                    error_logs_triggered.append('list_mfa_devices')

            if user.get('Arn'):
                try:
                    user['accessed_services'] = get_last_accessed_services(
                        client=iam_client,
                        arn=user['Arn'])
                except Exception:
                    if 'get_last_accessed_services' not in error_logs_triggered:
                        logger.exception(f'Unable to fetch the last accessed '
                                         f'services for {user}')
                        error_logs_triggered.append('get_last_accessed_services')
                    # fallthrough to continue discovery tasks, it's not critical data
            else:
                logger.warning(f'No Arn found for user: {user}')

            yield user, AwsUserType.Regular

    try:
        time_slept = 0
        root_user = None
        while iam_client.generate_credential_report()['State'] != 'COMPLETE':
            time.sleep(2)
            time_slept += 2
            if time_slept > 60 * 5:
                logger.error(f'Error - creds report took more than 5 minutes')
                raise ValueError(f'Error - creds report took more than 5 minutes')
        response = iam_client.get_credential_report()
        for user in list(csv.DictReader(response['Content'].decode('utf-8').splitlines(), delimiter=',')):
            if user.get('user') == '<root_account>':
                root_user = user
                break

        if not root_user:
            return None
        try:
            uses_virtual_mfa = False
            for page in iam_client.get_paginator('list_virtual_mfa_devices').paginate(AssignmentStatus='Any'):
                for virtual_mfa_device in (page.get('VirtualMFADevices') or []):
                    if 'mfa/root-account-mfa-device' in str(virtual_mfa_device).lower():
                        uses_virtual_mfa = True
                        break
                if uses_virtual_mfa:
                    break

            root_user['uses_virtual_mfa'] = uses_virtual_mfa

        except Exception:
            pass

        yield root_user, AwsUserType.Root
    except Exception:
        pass


def parse_root_user(user: AWSUserAdapter, root_user: dict):
    try:
        if root_user.get('arn'):
            user.id = root_user['arn']
            user.username = root_user['arn']
            user.user_create_date = parse_date(root_user.get('user_creation_time'))
            user.user_pass_last_used = parse_date(root_user.get('password_last_used'))
            user.has_administrator_access = True
            if root_user.get('mfa_active') == 'true':
                user.user_associated_mfa_devices.append(
                    AWSMFADevice()
                )
                user.has_associated_mfa_devices = True
            elif root_user.get('mfa_active') == 'false':
                user.user_associated_mfa_devices = []
                user.has_associated_mfa_devices = False

            for access_key_num in [1, 2]:
                access_key_status = root_user.get(f'access_key_{access_key_num}_active')
                if access_key_status:
                    access_key_status = 'Active' if access_key_status == 'true' else 'Inactive'
                else:
                    access_key_status = None
                user.user_attached_keys.append(
                    AWSIAMAccessKey(
                        status=access_key_status,
                        create_date=parse_date(root_user.get(f'access_key_{access_key_num}_last_rotated')),
                        last_used_time=parse_date(root_user.get(f'access_key_{access_key_num}_last_used_date')),
                        last_used_service=root_user.get(f'access_key_{access_key_num}_last_used_service'),
                        last_used_region=root_user.get(f'access_key_{access_key_num}_last_used_region')
                    ))

            if root_user.get('uses_virtual_mfa') is not None:
                user.uses_virtual_mfa = root_user.get('uses_virtual_mfa')

            if root_user.get('accessed_services') is not None:
                all_services = list()
                for service in root_user.get('accessed_services'):
                    try:
                        svc = AWSUserService(name=service.get('ServiceName'),
                                             namespace=service.get('ServiceNamespace'),
                                             authd_entities=service.get('TotalAuthenticatedEntities'),
                                             last_authenticated=parse_date(service.get('LastAuthenticated')),
                                             last_authenticated_entity=service.get('LastAuthenticatedEntity'))

                        all_services.append(svc)
                    except Exception:
                        logger.exception(f'Problem creating services list: {root_user}')
                        # fallthrough here to continue with other services

                user.accessed_services = all_services

            user.set_raw(root_user)

            return user
    except Exception:
        logger.exception(f'Failed parsing root user')
    return None


def parse_raw_data_inner_users(user: AWSUserAdapter, user_raw_data: Tuple[Dict, AwsUserType]):
    try:
        user_raw, user_type = user_raw_data
        if user_type == AwsUserType.Root:
            return parse_root_user(user, user_raw)

        # Else, this is a regular user
        if user_type == AwsUserType.Regular and user_raw.get('Arn'):
            if not user_raw.get('UserId'):
                logger.warning(f'Bad user {user_raw}')
                return None

            user.id = user_raw['UserId']
            user.username = user_raw.get('UserName')
            user.user_path = user_raw.get('Path')
            user.user_arn = user_raw.get('Arn')
            user.user_create_date = parse_date(user_raw.get('CreateDate'))
            user.user_pass_last_used = parse_date(user_raw.get('PasswordLastUsed'))
            user.user_is_password_enabled = user_raw.get('user_is_password_enabled') or False
            user.user_permission_boundary_arn = (user_raw.get('PermissionsBoundary') or {}).get(
                'PermissionsBoundaryArn'
            )
            user.has_administrator_access = user_raw.get('has_administrator_access') or False

            tags_dict = {i['Key']: (i.get('Value') or '') for i in (user_raw.get('Tags') or [])
                         if (isinstance(i, dict) and i.get('Key') and i.get('Value'))}

            for key, value in tags_dict.items():
                try:
                    user.aws_tags.append(AWSTagKeyValue(key=key, value=value))
                except Exception:
                    logger.exception(f'Problem adding tags: {user_raw}')

            try:
                user_groups = user_raw.get('groups')
                if isinstance(user_groups, list):
                    user.groups = user_groups
            except Exception:
                logger.exception(f'Problem adding user groups: {user_raw}')

            # iam group policies
            policies = user_raw.get('group_attached_policies') or []
            if isinstance(policies, list):
                try:
                    parse_iam_policy(user=user,
                                     policies=policies,
                                     policy_type='Group Managed')
                except Exception:
                    logger.exception(f'Unable to parse IAM group policy')
            else:
                logger.warning(f'Malformed policies. Expected list, got '
                               f'{type(policies)}: {str(policies)}')

            # iam user attached policies
            policies = user_raw.get('attached_policies') or []
            if isinstance(policies, list):
                try:
                    parse_iam_policy(user=user,
                                     policies=policies,
                                     policy_type='Managed')
                except Exception:
                    logger.exception(f'Unable to parse IAM user attached policy')
            else:
                logger.warning(f'Malformed policies. Expected list, got '
                               f'{type(policies)}: {str(policies)}')

            # iam user inline policies
            policies = user_raw.get('inline_policies') or []
            if isinstance(policies, list):
                try:
                    parse_iam_policy(user=user,
                                     policies=policies,
                                     policy_type='Inline')
                except Exception:
                    logger.exception(f'Unable to parse IAM user inline policy')
            else:
                logger.warning(f'Malformed policies. Expected list, got '
                               f'{type(policies)}: {str(policies)}')

            # iam access keys
            access_keys = user_raw.get('access_keys') or []
            for access_key_raw in access_keys:
                try:
                    access_key_status = access_key_raw.get('Status')
                    access_key_last_used = access_key_raw.get('AccessKeyLastUsed') or {}
                    user.user_attached_keys.append(
                        AWSIAMAccessKey(
                            access_key_id=access_key_raw.get('AccessKeyId'),
                            status=access_key_status if access_key_status in ['Active', 'Inactive'] else None,
                            create_date=parse_date(access_key_raw.get('CreateDate')),
                            last_used_time=parse_date(access_key_last_used.get('LastUsedDate')),
                            last_used_service=access_key_last_used.get('ServiceName'),
                            last_used_region=access_key_last_used.get('Region')
                        )
                    )
                except Exception:
                    logger.exception(f'Problem adding user access keys: {user_raw}')

            associated_mfa_devices = user_raw.get('mfa_devices') or []
            for associated_mfa_device_raw in associated_mfa_devices:
                try:
                    user.user_associated_mfa_devices.append(
                        AWSMFADevice(
                            serial_number=associated_mfa_device_raw.get('SerialNumber'),
                            enable_date=associated_mfa_device_raw.get('EnableDate')
                        )
                    )
                except Exception:
                    logger.exception(f'Problem parsing MFA device: {user_raw}')

            user.has_associated_mfa_devices = bool(associated_mfa_devices)

            if user_raw.get('accessed_services') is not None:
                all_services = list()
                for service in user_raw.get('accessed_services'):
                    try:
                        svc = AWSUserService(
                            name=service.get('ServiceName'),
                            namespace=service.get('ServiceNamespace'),
                            authd_entities=service.get('TotalAuthenticatedEntities'),
                            last_authenticated=parse_date(service.get('LastAuthenticated')),
                            last_authenticated_entity=service.get('LastAuthenticatedEntity'))

                        all_services.append(svc)
                    except Exception:
                        logger.exception(f'Problem creating services list: {user_raw}')
                        # fallthrough here to continue with other services

                user.accessed_services = all_services

            user.set_raw(user_raw)
            return user

        logger.error(f'Error - Type {user_type} does not exist')
        return None
    except Exception:
        logger.exception(f'Problem parsing user, continuing: {user_raw}')
    return None


def get_last_accessed_services(client: boto3.session.Session.client,
                               arn: str) -> list:
    """ This function takes the passed boto3 client object, configured
    for IAM, creates a job to pull the last accessed AWS services,
    waits for that job to finish, then builds a list of dictionary
    objects that are returned to the caller.

    :param client: A boto3 client object that is used to connect to the
    AWS IAM service.
    :param arn: The AWS Resource Name for an individual IAM user, role
    or group.
    :returns all_accessed_services: This is a list of all of the
    AWSUserService objects that describe the services that were consumed
    by the arn.
    """
    logger.debug(f'Started fetching user services last accessed for {arn}')
    try:
        job_id = client.generate_service_last_accessed_details(
            Arn=arn).get('JobId')
    except Exception as err:
        logger.exception(f'Failed to get a JobId for {arn}')
        return []

    try:
        job_id_waiter = create_custom_waiter(
            boto_client=client,
            name='JobId',
            operation='GetServiceLastAccessedDetails',
            argument='JobStatus')
        job_id_waiter.wait(JobId=job_id)
    except Exception as err:
        logger.exception(f'Waiter failed: {err}')
        # bail out... we can't do anything more and should continue discovery tasks
        return []

    all_accessed_services = list()
    try:
        for services_page in get_paginated_marker_api(functools.partial(
                client.get_service_last_accessed_details, JobId=job_id)):
            if not isinstance(services_page, dict):
                raise ValueError(f'Malformed services page, exptected a dict, '
                                 f'got {type(services_page)}: {str(services_page)}')

            for service in services_page.get('ServicesLastAccessed') or []:
                if not isinstance(service, dict):
                    raise ValueError(f'Malformed service, expected a dict, got '
                                     f'{type(service)}: {str(service)}')

                all_accessed_services.append(service)
    except Exception:
        logger.exception(f'Error in paginated handling.')
        # fallthrough to continue with other discovery tasks

    logger.debug(f'Finished fetching user services last accessed for {arn}')

    return all_accessed_services


def parse_iam_policy(user: AWSUserAdapter, policies: list, policy_type: str):
    logger.debug(f'Started parsing IAM {policy_type} policy for '
                 f'{user.user_arn}')

    for policy in policies:
        if not isinstance(policy, dict):
            raise ValueError(f'Malformed policy. Exptected a dict, got'
                             f'{type(policy)}: {str(policy)}')

        name = policy.get('name')
        if not isinstance(name, str):
            logger.warning(f'Malformed policy name. Expected a str, got '
                           f'{type(name)}: {str(name)}')
            continue

        if name == 'AdministratorAccess':
            user.has_administrator_access = True

        permissions = list()
        try:
            policy_permissions = policy.get('permissions')
            if not isinstance(policy_permissions, list):
                raise ValueError(f'Malformed policy permissions. Expected a '
                                 f'dict, got {type(policy_permissions)}:'
                                 f'{str(policy_permissions)}')

            for policy_permission in policy_permissions:
                if not isinstance(policy_permission, dict):
                    raise ValueError(f'Malformed policy permission. Expected a'
                                     f'dict, got {type(policy_permission)}'
                                     f'{str(policy_permission)}')

                permission = AWSIAMPolicyPermission(
                    policy_action=policy_permission.get('actions'),
                    policy_effect=policy_permission.get('effect'),
                    policy_resource=policy_permission.get('resource'),
                    policy_sid=policy_permission.get('sid'),
                )
                permissions.append(permission)
        except Exception:
            logger.exception(f'Unable to set policy permissions')
            # fallthrough

        try:
            policy_count = policy.get('attachment_count')
            if not isinstance(policy_count, int):
                logger.warning(f'Malformed policy count. Expected an int, got '
                               f'{type(policy_count)}: {str(policy_count)}')
                policy_count = None

            boundary_count = policy.get('permission_boundary_count')
            if not isinstance(boundary_count, int):
                logger.warning(f'Malformed permission boundary count. Expected '
                               f'an int, got {type(boundary_count)}:'
                               f'{str(boundary_count)}')
                boundary_count = None

            attachable = policy.get('is_attachable')
            if not isinstance(attachable, bool):
                logger.warning(f'Malformed attachable. Expected a bool, got '
                               f'{type(attachable)}: {str(attachable)}')
                attachable = None

            user.user_attached_policies.append(
                AWSIAMPolicy(
                    policy_arn=policy.get('arn'),
                    policy_attachment_count=policy_count,
                    policy_create_date=parse_date(policy.get('create_date')),
                    policy_description=policy.get('description'),
                    policy_id=policy.get('id'),
                    policy_is_attachable=attachable,
                    policy_name=name,
                    policy_permissions=permissions,
                    policy_permission_boundary_count=boundary_count,
                    policy_type=policy_type,
                    policy_updated_date=parse_date(policy.get('update_date')),
                    policy_version=policy.get('version'),
                    policy_version_id=policy.get('version_id'),
                )
            )
        except Exception:
            logger.exception(
                f'Problem adding user managed policies: {str(policies)}')
            raise
    logger.debug(f'Finished parsing IAM {policy_type} policy')
