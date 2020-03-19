import csv
import functools
import logging
import time
from enum import Enum, auto
from typing import Dict, Tuple

from aws_adapter.connection.structures import AWSMFADevice, AWSIAMAccessKey, AWSTagKeyValue, \
    AWSIAMPolicy, AWSUserAdapter
from aws_adapter.connection.utils import get_paginated_marker_api
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


class AwsUserType(Enum):
    Regular = auto()
    Root = auto()


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements, too-many-locals
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
                groups_attached_policies = []
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_groups_for_user, UserName=username)
                ):
                    for group_raw in (page.get('Groups') or []):
                        group_name = group_raw.get('GroupName')
                        if group_name:
                            groups.append(group_name)

                            try:
                                for agp_page in get_paginated_marker_api(
                                        functools.partial(
                                            iam_client.list_attached_group_policies, GroupName=group_name
                                        )
                                ):
                                    for attached_policy in agp_page['AttachedPolicies']:
                                        policy_name = attached_policy.get('PolicyName')
                                        if policy_name:
                                            groups_attached_policies.append(policy_name)
                            except Exception:
                                if 'list_attached_group_policies' not in error_logs_triggered:
                                    logger.exception(f'Problem with list_attached_group_policies')
                                    error_logs_triggered.append('list_attached_group_policies')

                user['groups'] = groups
                user['group_attached_policies'] = groups_attached_policies

                if 'AdministratorAccess' in groups_attached_policies:
                    user['has_administrator_access'] = True
            except Exception:
                if 'list_groups_for_users' not in error_logs_triggered:
                    logger.exception(f'Problem with list_groups_for_user')
                    error_logs_triggered.append('list_groups_for_users')

            try:
                attached_user_policies = []
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_attached_user_policies, UserName=username)
                ):
                    for attached_policy in (page.get('AttachedPolicies') or []):
                        policy_name = attached_policy.get('PolicyName')
                        if policy_name:
                            attached_user_policies.append(policy_name)

                user['attached_policies'] = attached_user_policies

                if 'AdministratorAccess' in attached_user_policies:
                    user['has_administrator_access'] = True
            except Exception:
                if 'list_attached_user_policies' not in error_logs_triggered:
                    logger.exception(f'Problem with list_attached_user_policies')
                    error_logs_triggered.append('list_attached_user_policies')

            try:
                inline_policies = []
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_user_policies, UserName=username)
                ):
                    inline_policies.extend(page.get('PolicyNames') or [])

                user['inline_policies'] = inline_policies

                if 'AdministratorAccess' in inline_policies:
                    user['has_administrator_access'] = True
            except Exception:
                if 'list_user_policies' not in error_logs_triggered:
                    logger.exception(f'Problem with list_user_policies')
                    error_logs_triggered.append('list_user_policies')

            try:
                access_keys = []
                for page in get_paginated_marker_api(
                        functools.partial(iam_client.list_access_keys, UserName=username)
                ):
                    for access_key_metadata in page.get('AccessKeyMetadata') or []:
                        access_key_id = access_key_metadata.get('AccessKeyId')
                        if access_key_id:
                            try:
                                response = iam_client.get_access_key_last_used(AccessKeyId=access_key_id)
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
                        functools.partial(iam_client.list_mfa_devices, UserName=username)
                ):
                    user['mfa_devices'].extend(mfa_devices_page.get('MFADevices') or [])
            except Exception:
                if 'list_mfa_devices' not in error_logs_triggered:
                    logger.exception(f'Problem with list_mfa_devices')
                    error_logs_triggered.append('list_mfa_devices')

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
        if user_type == AwsUserType.Regular:
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

            try:
                tags_dict = {i['Key']: i['Value'] for i in (user_raw.get('Tags') or [])}
                for key, value in tags_dict.items():
                    user.aws_tags.append(AWSTagKeyValue(key=key, value=value))
            except Exception:
                logger.exception(f'Problem adding tags')

            try:
                user_groups = user_raw.get('groups')
                if isinstance(user_groups, list):
                    user.groups = user_groups
            except Exception:
                logger.exception(f'Problem adding user groups')

            try:
                policies = user_raw.get('attached_policies') or []
                for policy in policies:
                    user.user_attached_policies.append(AWSIAMPolicy(policy_name=policy, policy_type='Managed'))
                    if policy == 'AdministratorAccess':
                        user.has_administrator_access = True
            except Exception:
                logger.exception(f'Problem adding user managed policies')

            try:
                policies = user_raw.get('inline_policies') or []
                for policy in policies:
                    user.user_attached_policies.append(AWSIAMPolicy(policy_name=policy, policy_type='Inline'))
                    if policy == 'AdministratorAccess':
                        user.has_administrator_access = True
            except Exception:
                logger.exception(f'Problem adding user inline policies')

            try:
                policies = user_raw.get('group_attached_policies') or []
                for policy in policies:
                    user.user_attached_policies.append(AWSIAMPolicy(policy_name=policy, policy_type='Group Managed'))
                    if policy == 'AdministratorAccess':
                        user.has_administrator_access = True
            except Exception:
                logger.exception(f'Problem adding user group managed policies')

            try:
                access_keys = user_raw.get('access_keys') or []
                for access_key_raw in access_keys:
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
                logger.exception(f'Problem adding user access keys')

            try:
                associated_mfa_devices = user_raw.get('mfa_devices') or []
                for associated_mfa_device_raw in associated_mfa_devices:
                    user.user_associated_mfa_devices.append(
                        AWSMFADevice(
                            serial_number=associated_mfa_device_raw.get('SerialNumber'),
                            enable_date=associated_mfa_device_raw.get('EnableDate')
                        )
                    )
                user.has_associated_mfa_devices = bool(associated_mfa_devices)
            except Exception:
                logger.exception(f'Problem parsing mfa devices')

            user.set_raw(user_raw)
            return user

        logger.error(f'Error - Type {user_type} does not exist')
        return None
    except Exception:
        logger.exception(f'Problem parsing user, continuing')
    return None
