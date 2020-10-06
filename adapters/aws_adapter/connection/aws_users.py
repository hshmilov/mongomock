import csv
import functools
import logging
import time
from enum import Enum, auto
from typing import Dict, Tuple

import boto3

from aws_adapter.connection.structures import AWSMFADevice, AWSIAMAccessKey, \
    AWSTagKeyValue, AWSIAMPolicy, AWSUserAdapter, AWSUserService, \
    AWSIAMPolicyPermission, AWSIAMPolicyCondition, AWSIAMPolicyTrustedEntity
from aws_adapter.connection.utils import get_paginated_marker_api, \
    create_custom_waiter, process_attached_iam_policy, process_inline_iam_policy
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


class AwsUserType(Enum):
    Regular = auto()
    Root = auto()
    Role = auto()


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-locals,
# pylint: disable=too-many-statements, logging-format-interpolation, too-many-lines
def query_users_by_client_for_all_sources(client_data, accessed_services: bool):
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
                                                raise ValueError(f'Malformed policy. '
                                                                 f'Expected dict, got '
                                                                 f'{type(policy)}: '
                                                                 f'{str(policy)}')

                                            policy_name = policy.get('PolicyName')
                                            if not isinstance(policy_name, str):
                                                if policy_name is not None:
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
                # fallthrough

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
                            if isinstance(policy, dict):
                                policy_name = policy.get('PolicyName')
                                if not isinstance(policy_name, str):
                                    if policy_name is not None:
                                        logger.warning(f'Malformed policy name, '
                                                       f'expected str, got '
                                                       f'{type(policy_name)}: '
                                                       f'{str(policy_name)}')
                                    continue

                                if policy_name == 'AdministratorAccess':
                                    user['has_administrator_access'] = True
                            else:
                                logger.warning(f'Malformed attached policy. '
                                               f'Expected dict, got '
                                               f'{type(policy)}: '
                                               f'{str(policy)}')
                                continue
                            try:
                                attached_user_policy = process_attached_iam_policy(
                                    iam_client=iam_client,
                                    attached_policy=policy)

                                if not isinstance(attached_user_policy, dict):
                                    raise ValueError(f'Malformed user policy. '
                                                     f'Expected dict, got '
                                                     f'{type(attached_user_policy)}: '
                                                     f'{str(attached_user_policy)}')

                                user['attached_policies'].append(attached_user_policy)

                            except Exception:
                                logger.exception(f'Unable to fetch user\'s '
                                                 f'attached policy.')
                                continue

            except Exception:
                if 'list_attached_user_policies' not in error_logs_triggered:
                    logger.exception(f'Problem with list_attached_user_policies')
                    error_logs_triggered.append('list_attached_user_policies')
                # fallthrough

            # user inline policies
            try:
                logger.debug(f'Fetching inline user policy')
                user['inline_policies'] = list()
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_user_policies,
                                          UserName=username)
                ):

                    if isinstance(page, dict):
                        policy_names = page.get('PolicyNames')
                        if isinstance(policy_names, list):
                            for inline_policy in policy_names:
                                if isinstance(inline_policy, str):
                                    if inline_policy == 'AdministratorAccess':
                                        user['has_administrator_access'] = True

                                    inline_user_policy = process_inline_iam_policy(
                                        client=iam_client,
                                        user_name=username,
                                        policy=inline_policy)

                                    if not isinstance(inline_user_policy, dict):
                                        logger.warning(f'Malformed inline user '
                                                       f'policy. Expected dict, got '
                                                       f'{type(inline_user_policy)}: '
                                                       f'{str(inline_user_policy)}')
                                        continue

                                    user['inline_policies'].append(inline_user_policy)
                                else:
                                    logger.warning(f'Malformed inline policies. '
                                                   f'Expected str, got '
                                                   f'{type(inline_policy)}: '
                                                   f'{str(inline_policy)}')
                                    continue
                        else:
                            if policy_names is not None:
                                logger.warning(f'Malformed policy names. Expected a'
                                               f'list, got {type(policy_names)}: '
                                               f'{str(policy_names)}')
                            continue
                    else:
                        if page is not None:
                            logger.warning(f'Malformed inline policy page, '
                                           f'expected a dict, got '
                                           f'{type(page)}: {str(page)}')
                        continue

            except Exception:
                if 'list_user_policies' not in error_logs_triggered:
                    logger.exception(f'Problem with list_user_policies')
                    error_logs_triggered.append('list_user_policies')
                # fallthrough

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
                if accessed_services:
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


# pylint: disable=no-else-return
def parse_raw_data_inner_users(user: AWSUserAdapter, user_raw_data: Tuple[Dict, AwsUserType]):
    try:
        user_raw, user_type = user_raw_data
        if user_type == AwsUserType.Root:
            return parse_root_user(user, user_raw)
        elif user_type == AwsUserType.Role:
            return parse_user_role(user, user_raw)

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
            argument='JobStatus',
            delay=3,
            max_attempts=12
        )
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
        if isinstance(policy, dict):
            name = policy.get('name')
            if not isinstance(name, str):
                if name is not None:
                    logger.warning(f'Malformed policy name. Expected a str, got '
                                   f'{type(name)}: {str(name)}')
                continue

            if name == 'AdministratorAccess':
                user.has_administrator_access = True

            permissions = list()
            try:
                policy_permissions = policy.get('permissions')
                if isinstance(policy_permissions, list):
                    for policy_permission in policy_permissions:
                        if isinstance(policy_permission, dict):
                            permission = AWSIAMPolicyPermission(
                                policy_action=policy_permission.get('actions'),
                                policy_effect=policy_permission.get('effect'),
                                policy_resource=policy_permission.get('resource'),
                                policy_sid=policy_permission.get('sid'),
                            )
                            permissions.append(permission)
                        else:
                            if policy_permission is not None:
                                logger.warning(f'Malformed policy permission. '
                                               f'Expected a dict, got '
                                               f'{type(policy_permission)}: '
                                               f'{str(policy_permission)}')
                            continue
                else:
                    if policy_permissions is not None:
                        logger.warning(f'Malformed policy permissions. Expected a '
                                       f'dict, got {type(policy_permissions)}:'
                                       f'{str(policy_permissions)}')
            except Exception:
                logger.exception(f'Unable to set policy permissions')
                # fallthrough
            try:
                policy_count = policy.get('attachment_count')
                if not isinstance(policy_count, int):
                    if policy_count is not None:
                        logger.warning(f'Malformed policy count. Expected an int, got '
                                       f'{type(policy_count)}: {str(policy_count)}')
                    policy_count = None

                boundary_count = policy.get('permission_boundary_count')
                if not isinstance(boundary_count, int):
                    if boundary_count is not None:
                        logger.warning(f'Malformed permission boundary count. Expected '
                                       f'an int, got {type(boundary_count)}:'
                                       f'{str(boundary_count)}')
                    boundary_count = None

                attachable = policy.get('is_attachable')
                if not isinstance(attachable, bool):
                    if attachable is not None:
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
                continue
        else:
            if policy is not None:
                logger.warning(f'Malformed policy. Expected a dict, got'
                               f'{type(policy)}: {str(policy)}')

    logger.debug(f'Finished parsing IAM {policy_type} policy')


# pylint: disable=inconsistent-return-statements
def query_roles_by_client_for_all_sources(client_data):
    iam_client = client_data.get('iam')
    if not iam_client:
        return None

    error_logs_triggered = []

    # fetch roles as users
    try:
        for roles_page in get_paginated_marker_api(iam_client.list_roles):
            if isinstance(roles_page, dict):
                roles = roles_page.get('Roles')
                if roles and isinstance(roles, list):
                    for role in roles:
                        if not isinstance(role, dict):
                            raise ValueError(f'Malformed role. Expected a dict,'
                                             f' got {type(role)}: {str(role)}')

                        role_name = role.get('RoleName')
                        if not (role_name and isinstance(role_name, str)):
                            raise ValueError(
                                f'Malformed role name. Expected a str, '
                                f'got {type(role_name)}: '
                                f'{str(role_name)}')
                        new_role = dict()
                        new_role['assume_role_policy'] = list()

                        # assume role policy
                        assume_role_policy_document = role.get('AssumeRolePolicyDocument')
                        if isinstance(assume_role_policy_document, dict):
                            # compile the assume role policy for the role
                            assume_role_policy = dict()
                            assume_role_policy['version'] = assume_role_policy_document.get('Version')
                            assume_role_policy['statements'] = list()

                            statements = assume_role_policy_document.get('Statement')
                            if isinstance(statements, list):
                                for statement in statements:
                                    if isinstance(statement, dict):
                                        policy_actions = list()

                                        # can get a str or a list here
                                        actions = statement.get('Action')
                                        if isinstance(actions, str):
                                            policy_actions = [actions]
                                        if isinstance(actions, list):
                                            policy_actions = actions

                                        statement_dict = dict()
                                        statement_dict['actions'] = list()
                                        statement_dict['actions'].extend(policy_actions)
                                        statement_dict['effect'] = statement.get('Effect')
                                        statement_dict['sid'] = statement.get('Sid')
                                        statement_dict['condition'] = list()
                                        statement_dict['principal'] = list()

                                        condition = statement.get('Condition')
                                        if isinstance(condition, dict):
                                            # only 1 operator is returned in all cases
                                            condition_operators = list(condition.keys())
                                            if isinstance(condition_operators, list):
                                                for condition_operator in condition_operators:
                                                    if isinstance(condition_operator, str):
                                                        conditions = condition[condition_operator]
                                                        if isinstance(conditions, dict):
                                                            condition_key = None
                                                            condition_value = None
                                                            for k, v in conditions.items():
                                                                condition_key = k or ''
                                                                condition_value = v or ''

                                                                statement_dict['condition'].append(
                                                                    (condition_operator,
                                                                     condition_key,
                                                                     condition_value))
                                                        else:
                                                            if conditions is not None:
                                                                logger.warning(f'Malformed conditions. '
                                                                               f'Expected a dict, got '
                                                                               f'{type(conditions)}:'
                                                                               f'{str(conditions)}')
                                                    else:
                                                        if condition_operator is not None:
                                                            logger.warning(
                                                                f'Malformed condition operator. '
                                                                f'Expected a str, got '
                                                                f'{type(condition_operator)}: '
                                                                f'{str(condition_operator)}')
                                            else:
                                                if condition_operators is not None:
                                                    logger.warning(
                                                        f'Malformed condition operators. '
                                                        f'Expected a list, got '
                                                        f'{type(condition_operators)}: '
                                                        f'{str(condition_operators)}')
                                        else:
                                            if condition is not None:
                                                logger.warning(
                                                    f'Malformed condition statement. '
                                                    f'Expected a dict, got '
                                                    f'{type(condition)}: {str(condition)}')

                                        principal = statement.get('Principal')
                                        if isinstance(principal, dict):
                                            principal_type = None
                                            principal_name = None
                                            for k, v in principal.items():
                                                principal_type = k or ''
                                                principal_name = v or ''

                                                statement_dict['principal'].append(
                                                    (principal_type, principal_name))

                                            assume_role_policy['statements'].append(
                                                statement_dict)
                                        else:
                                            if principal is not None:
                                                logger.warning(f'Malformed principal. '
                                                               f'Expected a dict, '
                                                               f'got {type(principal)}:'
                                                               f' {str(principal)}')
                                    else:
                                        if statement is not None:
                                            logger.warning(
                                                f'Malformed statement. Expected a '
                                                f'dict, got {type(statement)}: '
                                                f'{str(statement)}')
                            else:
                                if statements is not None:
                                    logger.warning(
                                        f'Malformed assume role statement. '
                                        f'Expected a list, got {type(statements)}: '
                                        f'{str(statements)}')

                            new_role['assume_role_policy'].append(
                                assume_role_policy)
                        else:
                            if assume_role_policy_document is not None:
                                logger.warning(f'Malformed assume role policy '
                                               f'document. Expected a dict, got '
                                               f'{type(assume_role_policy_document)}: '
                                               f'{str(assume_role_policy_document)}')

                        # enrich the role data
                        try:
                            role_data_raw = iam_client.get_role(RoleName=role_name)
                            if not isinstance(role_data_raw, dict):
                                raise ValueError(f'Malformed raw role data. Expected a '
                                                 f'dict, got {type(role_data_raw)}: '
                                                 f'{str(role_data_raw)}')

                            role_data = role_data_raw.get('Role')
                            if isinstance(role_data, dict):
                                new_role['arn'] = role_data.get('Arn')
                                new_role['create_date'] = role_data.get('CreateDate')
                                new_role['description'] = role_data.get('Description')
                                new_role['max_session'] = role_data.get('MaxSessionDuration')
                                new_role['path'] = role_data.get('Path')
                                new_role['role_id'] = role_data.get('RoleId')
                                new_role['role_name'] = role_name
                                new_role['last_activity'] = role_data.get('RoleLastUsed')
                                new_role['tags'] = role_data.get('Tags')
                            else:
                                if role_data is not None:
                                    logger.warning(f'Malformed raw role data. '
                                                   f'Expected a dict, got '
                                                   f'{type(role_data)}: '
                                                   f'{str(role_data)}')
                        except Exception:
                            logger.warning(f'Unable to enrich the role data.')

                        # get attached policies
                        try:
                            new_role['role_attached_policies'] = list()
                            for roles_attached_policies_page in get_paginated_marker_api(
                                    functools.partial(
                                        iam_client.list_attached_role_policies,
                                        RoleName=role_name)):
                                if isinstance(roles_attached_policies_page, dict):
                                    attached_policies = roles_attached_policies_page.get('AttachedPolicies')
                                    if isinstance(attached_policies, list):
                                        for attached_policy in attached_policies:
                                            if isinstance(attached_policy, dict):
                                                new_role['role_attached_policies'].append(
                                                    process_attached_iam_policy(iam_client,
                                                                                attached_policy))
                                            else:
                                                if attached_policy is not None:
                                                    logger.warning(
                                                        f'Malformed attached policy. '
                                                        f'Expected a dict, got '
                                                        f'{type(attached_policy)}: '
                                                        f'{str(attached_policy)}')
                                    else:
                                        if attached_policies is not None:
                                            logger.warning(
                                                f'Malformed attached policies. '
                                                f'Expected a list, got '
                                                f'{type(attached_policies)}:'
                                                f'{str(attached_policies)}')
                                else:
                                    if roles_attached_policies_page is not None:
                                        logger.warning(
                                            f'Malformed role attached policies '
                                            f'page. Expected a dict, got '
                                            f'{type(roles_attached_policies_page)}:'
                                            f'{str(roles_attached_policies_page)}')
                        except Exception:
                            if 'list_attached_role_policies' not in error_logs_triggered:
                                logger.exception(
                                    f'Problem with list_attached_role_policies')
                                error_logs_triggered.append('list_attached_role_policies')

                        # get inline policies
                        try:
                            new_role['role_inline_policies'] = list()
                            for roles_inline_policies_page in get_paginated_marker_api(
                                    functools.partial(
                                        iam_client.list_role_policies,
                                        RoleName=role_name)):
                                if isinstance(roles_inline_policies_page, dict):
                                    inline_policy_names = roles_inline_policies_page.get('PolicyNames')
                                    if isinstance(inline_policy_names, list):
                                        for inline_policy_name in inline_policy_names:
                                            if isinstance(inline_policy_name, str):
                                                try:
                                                    inline_policy_raw = iam_client.get_role_policy(
                                                        RoleName=role_name,
                                                        PolicyName=inline_policy_name)
                                                except Exception:
                                                    if 'get_role_policy' not in error_logs_triggered:
                                                        logger.exception(
                                                            f'Problem with get_role_policy')
                                                        error_logs_triggered.append(
                                                            'get_role_policy')
                                                    continue
                                                if isinstance(inline_policy_raw, dict):
                                                    inline_policy = inline_policy_raw.get('PolicyDocument')
                                                    if isinstance(inline_policy, dict):
                                                        new_policy = dict()
                                                        new_policy['name'] = inline_policy_name
                                                        new_policy['version'] = inline_policy.get('Version')

                                                        policy_statements = inline_policy.get('Statement')
                                                        if isinstance(policy_statements, list):
                                                            # get the permission actions
                                                            policy_actions = list()
                                                            for statement in policy_statements:
                                                                if isinstance(statement, dict):
                                                                    # can get a str or a list here
                                                                    actions = statement.get('Action')
                                                                    if isinstance(actions, str):
                                                                        policy_actions = [actions]
                                                                    if isinstance(actions, list):
                                                                        policy_actions = actions

                                                                    actions_dict = dict()
                                                                    actions_dict['effect'] = statement.get('Effect')
                                                                    actions_dict['resource'] = statement.get('Resource')
                                                                    actions_dict['actions'] = policy_actions
                                                                    actions_dict['sid'] = statement.get('Sid')

                                                                    new_role['role_inline_policies'].append(
                                                                        actions_dict)
                                                                else:
                                                                    if statement is not None:
                                                                        logger.warning(f'Malformed statement. '
                                                                                       f'Expected dict, got '
                                                                                       f'{type(statement)}: '
                                                                                       f'{str(statement)}')
                                                        else:
                                                            if policy_statements is not None:
                                                                logger.warning(
                                                                    f'Malformed policy statements. '
                                                                    f'Expected list, got '
                                                                    f'{type(policy_statements)}: '
                                                                    f'{str(policy_statements)}')
                                                    else:
                                                        if inline_policy is not None:
                                                            logger.warning(
                                                                f'Malformed inline policy. '
                                                                f'Expected a dict, got'
                                                                f'{type(inline_policy)}:'
                                                                f'{str(inline_policy)}')
                                                else:
                                                    if inline_policy_raw is not None:
                                                        logger.warning(f'Malformed raw inline policy.'
                                                                       f'Expected a dict, got '
                                                                       f'{type(inline_policy_raw)}:'
                                                                       f'{str(inline_policy_raw)}')
                                            else:
                                                if inline_policy_name is not None:
                                                    logger.warning(
                                                        f'Malformed inline policy '
                                                        f'name. Expected a str, '
                                                        f'got {type(inline_policy_name)}:'
                                                        f'{str(inline_policy_name)}')
                                    else:
                                        if inline_policy_names is not None:
                                            logger.warning(f'Malformed inline policies. '
                                                           f'Expected a list, got '
                                                           f'{type(inline_policy_names)}:'
                                                           f'{str(inline_policy_names)}')
                                else:
                                    if roles_inline_policies_page is not None:
                                        logger.warning(
                                            f'Malformed role inline policies '
                                            f'page. Expected a dict, got '
                                            f'{type(roles_inline_policies_page)}:'
                                            f'{str(roles_inline_policies_page)}')
                        except Exception:
                            if 'list_role_policies' not in error_logs_triggered:
                                logger.exception(
                                    f'Problem with list_role_policies')
                                error_logs_triggered.append('list_role_policies')
                            continue

                        yield new_role, AwsUserType.Role
                else:
                    if roles is not None:
                        logger.warning(f'Malformed extracted roles. Expected a '
                                       f'list, got {type(roles)}: {str(roles)}')
            else:
                if roles_page is not None:
                    logger.warning(f'Malformed roles page. Expected a dict, got '
                                   f'{type(roles_page)}: {str(roles_page)}')
    except Exception:
        if 'list_roles' not in error_logs_triggered:
            logger.exception(
                f'Problem with list_roles')
            error_logs_triggered.append('list_roles')


def parse_user_role(role: AWSUserAdapter, role_raw: dict):
    logger.debug(f'Started parsing role: {role_raw.get("arn")} as user')
    try:
        role.id = role_raw.get('role_id')
        role.role_id = role_raw.get('role_id')
        role.username = role_raw.get('role_name')
        role.role_name = role_raw.get('role_name')
        role.role_description = role_raw.get('description')
        role.user_create_date = parse_date(role_raw.get('create_date'))
        role.role_arn = role_raw.get('arn')
        role.role_max_session_duration = role_raw.get('max_session')
        role.role_path = role_raw.get('path')

        last_activity = role_raw.get('last_activity') or {}
        role.last_activity_time = parse_date(last_activity.get('LastUsedDate'))
        role.last_activity_region = last_activity.get('Region')
        role.tags = _parse_role_tags(role_raw)

        # assume role policy
        assume_role_policies = role_raw.get('assume_role_policy')
        if isinstance(assume_role_policies, list):
            for assume_role_policy in assume_role_policies:
                if isinstance(assume_role_policy, dict):
                    policies = assume_role_policy.get('statements')
                    if isinstance(policies, list):
                        for policy in policies:
                            if isinstance(policy, dict):
                                principals = list()
                                conditions = list()
                                trusted_entities = list()
                                policy_principal = policy.get('principal')
                                if isinstance(policy_principal, list):
                                    for principal in policy_principal:
                                        if isinstance(principal, tuple):
                                            principal_type, principal_name = principal
                                            try:
                                                trusted_entity = AWSIAMPolicyTrustedEntity(
                                                    type=principal_type,
                                                    name=principal_name
                                                )
                                                trusted_entities.append(trusted_entity)
                                            except Exception:
                                                if principal is not None:
                                                    logger.exception(f'Malformed policy '
                                                                     f'principal: '
                                                                     f'{str(principal)}')
                                                continue
                                        else:
                                            if principal is not None:
                                                logger.warning(
                                                    f'Malformed principal. Expected '
                                                    f'a tuple, got {type(principal)}: '
                                                    f'{str(principal)}')
                                            continue
                                else:
                                    if policy_principal is not None:
                                        logger.warning(f'Malformed policy principal. Expected a '
                                                       f'list, got {type(policy_principal)}: '
                                                       f'{str(policy_principal)}')

                                policy_condition = policy.get('condition')
                                if isinstance(policy_condition, list):
                                    for condition in policy_condition:
                                        if isinstance(condition, tuple):
                                            condition_operator, condition_key, condition_value = condition
                                            try:
                                                condition_instance = AWSIAMPolicyCondition(
                                                    condition_operator=condition_operator,
                                                    condition_key=condition_key,
                                                    condition_value=condition_value
                                                )
                                                conditions.append(condition_instance)
                                            except Exception:
                                                if condition is not None:
                                                    logger.exception(f'Malformed policy '
                                                                     f'condition: '
                                                                     f'{str(condition)}')
                                                continue
                                        else:
                                            if condition is not None:
                                                logger.warning(f'Malformed condition. '
                                                               f'Expected a tuple, '
                                                               f'got {type(condition)}: '
                                                               f'{str(condition)}')
                                            continue
                                else:
                                    if policy_condition is not None:
                                        logger.warning(
                                            f'Malformed policy condition. '
                                            f'Expected a list, got '
                                            f'{type(policy_condition)}: '
                                            f'{str(policy_condition)}')

                                policy_permission = AWSIAMPolicyPermission(
                                    policy_action=policy.get('actions'),
                                    policy_conditions=conditions,
                                    policy_effect=policy.get('effect'),
                                    policy_principals=principals,   # Deprecated in favor of Policies trusted_entity
                                    policy_sid=policy.get('sid')
                                )

                                role_assumed_policy = AWSIAMPolicy(
                                    trusted_entities=trusted_entities,
                                    policy_permissions=[policy_permission],
                                    policy_version=assume_role_policy.get(
                                        'version')
                                )
                                role.role_assume_role_policy_document.append(
                                    role_assumed_policy)
                            else:
                                if policy is not None:
                                    logger.warning(f'Malformed policy. Expected a '
                                                   f'dict, got {type(policy)}: '
                                                   f'{str(policy)}')
                    else:
                        if policies is not None:
                            logger.warning(f'Malformed policies. Expected a '
                                           f'list, got {type(policies)}: '
                                           f'{str(policies)}')
                else:
                    if assume_role_policy is not None:
                        logger.warning(f'Malformed assume role policy. Expected a '
                                       f'dict, got {type(assume_role_policy)}: '
                                       f'{str(assume_role_policy)}')
        else:
            if assume_role_policies is not None:
                logger.warning(f'Malformed assume role policies. Expected a '
                               f'list, got {type(assume_role_policies)}: '
                               f'{str(assume_role_policies)}')

        # attached policies
        attached_policies = role_raw.get('role_attached_policies')
        if isinstance(attached_policies, list):
            policy_permissions = list()

            for attached_policy in attached_policies:
                if isinstance(attached_policy, dict):
                    permissions = attached_policy.get('permissions')
                    if not (permissions and isinstance(permissions, list)):
                        logger.warning(
                            f'Malformed attached policy permissions. Expected '
                            f'a list, got {type(permissions)}: {str(permissions)}')
                        continue
                    for permission in permissions:
                        if isinstance(permission, dict):
                            statement = AWSIAMPolicyPermission(
                                policy_action=permission.get('actions'),
                                policy_effect=permission.get('effect'),
                                policy_resource=permission.get('resource'),
                                policy_sid=permission.get('sid')
                            )
                            policy_permissions.append(statement)
                        else:
                            if permission is not None:
                                logger.warning(
                                    f'Malformed permission. Expected a dict, '
                                    f'got {type(permission)}: '
                                    f'{str(permission)}')

                    attached_role_policy = AWSIAMPolicy(
                        policy_attachment_count=attached_policy.get(
                            'attachment_count'),
                        policy_create_date=parse_date(attached_policy.get('create_date')),
                        policy_description=attached_policy.get('description'),
                        policy_id=attached_policy.get('id'),
                        policy_is_attachable=attached_policy.get('is_attachable'),
                        policy_name=attached_policy.get('name'),
                        policy_permission_boundary_count=attached_policy.get(
                            'permission_boundary_count'),
                        policy_permissions=policy_permissions,
                        policy_updated_date=parse_date(attached_policy.get('update_date')),
                        policy_version_id=attached_policy.get('version_id'),
                        policy_version=attached_policy.get('version'),
                    )
                    role.role_attached_policies.append(attached_role_policy)
                else:
                    logger.warning(f'Malformed attached policy. Expected a '
                                   f'dict, got {type(attached_policy)}: '
                                   f'{str(attached_policy)}')
        else:
            if attached_policies is not None:
                logger.warning(f'Malformed attached policies. Expected a list, '
                               f'got {type(attached_policies)}'
                               f'{str(attached_policies)}')

        # inline policies
        inline_policies = role_raw.get('role_inline_policies')
        if isinstance(inline_policies, list):
            policy_permissions = list()

            for inline_policy in inline_policies:
                if isinstance(inline_policy, dict):
                    statement = AWSIAMPolicyPermission(
                        policy_action=inline_policy.get('actions') or [],
                        policy_effect=inline_policy.get('effect'),
                        policy_resource=inline_policy.get('resource'),
                        policy_sid=inline_policy.get('sid')
                    )
                    policy_permissions.append(statement)

                    role_policy = AWSIAMPolicy(
                        policy_attachment_count=inline_policy.get('attachment_count'),
                        policy_create_date=parse_date(inline_policy.get('create_date')),
                        policy_description=inline_policy.get('description'),
                        policy_id=inline_policy.get('id'),
                        policy_is_attachable=inline_policy.get('is_attachable'),
                        policy_name=inline_policy.get('name'),
                        policy_permission_boundary_count=inline_policy.get('permission_boundary_count'),
                        policy_permissions=policy_permissions,
                        policy_updated_date=parse_date(inline_policy.get('update_date')),
                        policy_version_id=inline_policy.get('version_id'),
                        policy_version=inline_policy.get('version'),
                    )
                    role.role_inline_policies.append(role_policy)

                    logger.debug(f'Finished parsing role {role_raw.get("arn")}'
                                 f' as user')
                else:
                    if inline_policy is not None:
                        logger.warning(f'Malformed inline policy. Expected a dict, '
                                       f'got {type(inline_policy)}: '
                                       f'{str(inline_policy)}')
        else:
            if inline_policies is not None:
                logger.warning(f'Malformed inline policies. Expected a list, got '
                               f'{type(inline_policies)}: {str(inline_policies)}')
    except Exception:
        logger.exception(f'Unable to parse user role')

    return role


def _parse_role_tags(role_raw: dict):
    tags = []
    raw_tags = role_raw.get('tags')
    if not isinstance(raw_tags, list):
        if raw_tags is not None:
            logger.warning(f'Got unexpected type of role tags:{str(role_raw)}')
        raw_tags = []

    for raw_tag in raw_tags:
        if isinstance(raw_tag, dict):
            tags.append(
                AWSTagKeyValue(
                    key=raw_tag.get('Key'),
                    value=raw_tag.get('Value')
                )
            )
    return tags
