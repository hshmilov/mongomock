"""
Contains all the scored rules for the "IAM" Category of AWS CIS
"""
# pylint: disable=invalid-triple-quote
import csv
import datetime
import logging
import time

import boto3
from botocore.exceptions import ClientError

from axonius.clients.aws.aws_clients import get_boto3_client_by_session
from axonius.utils.datetime import parse_date
from compliance.utils.account_report import AccountReport, RuleStatus
from compliance.utils.cis_utils import bad_api_response, good_api_response, get_api_error, cis_rule, \
    AWS_CIS_DEFAULT_REGION, get_api_data, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')
CREDS_REPORT_DELAY_TIME_IN_SECONDS = 2
MAX_SECONDS_TO_WAIT_FOR_CREDS_REPORT = 60 * 5   # 5 minutes


# Helper functions
def get_credential_report(iam_client):
    time_slept = 0
    try:
        while True:
            try:
                if iam_client.generate_credential_report()['State'] == 'COMPLETE':
                    break
            except ClientError as err:
                # pylint: disable=no-member
                if 'Rate exceeded' in err.error.get('Message', 'Unknown'):
                    time.sleep(CREDS_REPORT_DELAY_TIME_IN_SECONDS)
                    continue
                raise
            time.sleep(CREDS_REPORT_DELAY_TIME_IN_SECONDS)
            time_slept += CREDS_REPORT_DELAY_TIME_IN_SECONDS
            if time_slept > MAX_SECONDS_TO_WAIT_FOR_CREDS_REPORT:
                logger.error(f'Error - creds report took more than {CREDS_REPORT_DELAY_TIME_IN_SECONDS} seconds')
                return bad_api_response('Error - timed out generating iam credential report')
        response = iam_client.get_credential_report()
        return good_api_response(list(csv.DictReader(response['Content'].decode('utf-8').splitlines(), delimiter=',')))
    except Exception as e:
        if 'An error occurred (AccessDenied)' not in str(e):
            logger.exception(f'Exception while generating credential report')
        return bad_api_response(
            f'Error generating credential report (iam.generate_credential_report, iam.get_credential_report) - {str(e)}'
        )


def get_password_policy(iam_client):
    try:
        policy = iam_client.get_account_password_policy()
        if 'PasswordPolicy' not in policy:
            return ValueError(f'Bad response - can not find "PasswordPolicy" in response')

        return good_api_response(policy['PasswordPolicy'])
    except Exception as e:
        if 'An error occurred (AccessDenied)' not in str(e) and 'An error occurred (NoSuchEntity)' not in str(e):
            logger.exception('Exception while getting account password policy')
        return bad_api_response(f'Error getting account password policy (iam.get_account_password_policy API): '
                                f'{str(e)}')


def get_account_summary(iam_client):
    try:
        summary = iam_client.get_account_summary()
        if 'SummaryMap' not in summary:
            return ValueError(f'Bad response - can not find "SummaryMap" in response')

        return good_api_response(summary['SummaryMap'])
    except Exception as e:
        if 'An error occurred (AccessDenied)' not in str(e):
            logger.exception('Exception while getting account summary')
        return bad_api_response(f'Error getting account summary (iam.get_account_summary API): '
                                f'{str(e)}')


# Rules
class CISAWSCategory1:
    def __init__(self, report: AccountReport, session: boto3.Session, account_dict: dict):
        self.report = report
        self.account_name = account_dict.get('name') or ''
        self.region_name = AWS_CIS_DEFAULT_REGION if account_dict.get('get_all_regions') \
            else account_dict.get('region_name')
        self.https_proxy = account_dict.get('https_proxy')
        self.iam_client = get_boto3_client_by_session('iam', session, self.region_name, self.https_proxy)
        self.credential_report = get_credential_report(self.iam_client)
        self.password_policy = get_password_policy(self.iam_client)
        self.account_summary = get_account_summary(self.iam_client)
        self.account_id = account_dict.get('account_id_number')

    @cis_rule('1.1')
    def check_cis_aws_1_1(self, **kwargs):
        """
        1.1 Avoid the use of the "root" account (scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.credential_report)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.credential_report)
        for user in data:
            if user['user'] == '<root_account>':
                password_last_used = parse_date(user.get('password_last_used'))
                access_key_1_last_used_date = parse_date(user.get('access_key_1_last_used_date'))
                access_key_2_last_used_date = parse_date(user.get('access_key_2_last_used_date'))

                error_messages = []
                a_month_ago = datetime.datetime.utcnow().astimezone(datetime.timezone.utc) - datetime.timedelta(days=30)
                if password_last_used and password_last_used > a_month_ago:
                    error_messages.append(
                        f'Root account has been used with password in the last 30 days: {password_last_used}'
                    )
                if access_key_1_last_used_date and access_key_1_last_used_date > a_month_ago:
                    error_messages.append(
                        f'Access Key 1 has been used with password in the last 30 days: {access_key_1_last_used_date}'
                    )
                if access_key_2_last_used_date and access_key_2_last_used_date > a_month_ago:
                    error_messages.append(
                        f'Access Key 2 has been used with password in the last 30 days: {access_key_2_last_used_date}'
                    )

                if error_messages:
                    self.report.add_rule(
                        RuleStatus.Failed,
                        rule_section,
                        (1, 1),
                        1,
                        errors_to_gui(error_messages),
                        {
                            'type': 'users',
                            'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                                     f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                                     f'(data.aws_account_id == "{self.account_id or ""}")])'
                        }
                    )
                else:
                    self.report.add_rule(
                        RuleStatus.Passed,
                        rule_section,
                        (0, 1),
                        0,
                        ''
                    )
                break
        else:
            self.report.add_rule_error(rule_section, 'Could not find the root account in the credentials report')

    # pylint: disable=unnecessary-pass
    @cis_rule('1.2')
    def check_cis_aws_1_2(self, **kwargs):
        """
        1.2  Ensure multi-factor authentication (MFA) is enabled for all IAM users that have a console password (scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.credential_report)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.credential_report)
        failed_users = []
        for user in data:
            if user['password_enabled'].lower() == 'true' and user['mfa_active'].lower() == 'false':
                failed_users.append(f'User "{user["user"]}" ({user["arn"]}) '
                                    f'has password enabled but does not have MFA enabled')

        if failed_users:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(failed_users), len(data)),
                len(failed_users),
                errors_to_gui(failed_users),
                {
                    'type': 'users',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, len(data)),
                0,
                ''
            )

    @cis_rule('1.3')
    def check_cis_aws_1_3(self, **kwargs):
        """
        1.3  Ensure credentials unused for 90 days or greater are disabled (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.credential_report)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.credential_report)
        failed_users = 0
        failed_entities = 0
        overall_entities = 0
        error_messages = []
        for user in data:
            password_enabled = user['password_enabled'] == 'true'
            password_last_used = parse_date(user.get('password_last_used'))
            access_key_1_enabled = user['access_key_1_active'] == 'true'
            access_key_1_last_used_date = parse_date(user.get('access_key_1_last_used_date'))
            access_key_2_enabled = user['access_key_2_active'] == 'true'
            access_key_2_last_used_date = parse_date(user.get('access_key_2_last_used_date'))

            a_90_days_ago = datetime.datetime.utcnow().astimezone(datetime.timezone.utc) - datetime.timedelta(days=90)

            user_failed = False
            if password_enabled:
                overall_entities += 1
                if password_last_used and password_last_used < a_90_days_ago:
                    user_failed = True
                    failed_entities += 1
                    error_messages.append(f'Password for user "{user["user"]}" ({user["arn"]}) '
                                          f'has been used at {password_last_used}')

            if access_key_1_enabled:
                overall_entities += 1
                if access_key_1_last_used_date and access_key_1_last_used_date < a_90_days_ago:
                    user_failed = True
                    failed_entities += 1
                    error_messages.append(f'Access Key 1 for user "{user["user"]}" ({user["arn"]}) '
                                          f'has been used at {access_key_1_last_used_date}')

            if access_key_2_enabled:
                overall_entities += 1
                if access_key_2_last_used_date and access_key_2_last_used_date < a_90_days_ago:
                    user_failed = True
                    failed_entities += 1
                    error_messages.append(f'Access Key 2 for user "{user["user"]}" ({user["arn"]}) '
                                          f'has been used at {access_key_2_last_used_date}')

            if user_failed:
                failed_users += 1

        if error_messages:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (failed_entities, overall_entities),
                failed_users,
                errors_to_gui(error_messages),
                {
                    'type': 'users',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, overall_entities),
                0,
                ''
            )

    @cis_rule('1.4')
    def check_cis_aws_1_4(self, **kwargs):
        """
        1.4 Ensure access keys are rotated every 90 days or less (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.credential_report)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.credential_report)
        failed_users = 0
        failed_entities = 0
        overall_entities = 0
        error_messages = []
        for user in data:
            access_key_1_enabled = user['access_key_1_active'] == 'true'
            access_key_1_last_rotated = parse_date(user.get('access_key_1_last_rotated'))
            access_key_2_enabled = user['access_key_2_active'] == 'true'
            access_key_2_last_rotated = parse_date(user.get('access_key_2_last_rotated'))

            a_90_days_ago = datetime.datetime.utcnow().astimezone(datetime.timezone.utc) - datetime.timedelta(days=90)

            user_failed = False
            if access_key_1_enabled:
                overall_entities += 1
                if access_key_1_last_rotated and access_key_1_last_rotated < a_90_days_ago:
                    user_failed = True
                    failed_entities += 1
                    error_messages.append(f'Access Key 1 for user "{user["user"]}" ({user["arn"]}) '
                                          f'has last been rotated at {access_key_1_last_rotated}')

            if access_key_2_enabled:
                overall_entities += 1
                if access_key_2_last_rotated and access_key_2_last_rotated < a_90_days_ago:
                    user_failed = True
                    failed_entities += 1
                    error_messages.append(f'Access Key 2 for user "{user["user"]}" ({user["arn"]}) '
                                          f'has last been rotated at {access_key_2_last_rotated}')

            if user_failed:
                failed_users += 1

        if error_messages:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (failed_entities, overall_entities),
                failed_users,
                errors_to_gui(error_messages),
                {
                    'type': 'users',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, overall_entities),
                0,
                ''
            )

    @cis_rule('1.5')
    def check_cis_aws_1_5(self, **kwargs):
        """
        1.5 Ensure IAM password policy requires at least one uppercase letter (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.password_policy)
        if error:
            if 'NoSuchEntity' in error:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'Password policy does not exist'
                )
            else:
                self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.password_policy)
        if data.get('RequireUppercaseCharacters') is True:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )
        else:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                0,
                'Password policy does not require at least one uppercase letter'
            )

    @cis_rule('1.6')
    def check_cis_aws_1_6(self, **kwargs):
        """
        1.6 Ensure IAM password policy require at least one lowercase letter (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.password_policy)
        if error:
            if 'NoSuchEntity' in error:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'Password policy does not exist'
                )
            else:
                self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.password_policy)
        if data.get('RequireLowercaseCharacters') is True:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )
        else:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                0,
                'Password policy does not require at least one lowercase letter'
            )

    @cis_rule('1.7')
    def check_cis_aws_1_7(self, **kwargs):
        """
        1.7 Ensure IAM password policy require at least one symbol (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.password_policy)
        if error:
            if 'NoSuchEntity' in error:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'Password policy does not exist'
                )
            else:
                self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.password_policy)
        if data.get('RequireSymbols') is True:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )
        else:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                0,
                'Password policy does not require at least one symbol'
            )

    @cis_rule('1.8')
    def check_cis_aws_1_8(self, **kwargs):
        """
        1.8 Ensure IAM password policy require at least one number (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.password_policy)
        if error:
            if 'NoSuchEntity' in error:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'Password policy does not exist'
                )
            else:
                self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.password_policy)
        if data.get('RequireNumbers') is True:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )
        else:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                0,
                'Password policy does not require at least one number'
            )

    @cis_rule('1.9')
    def check_cis_aws_1_9(self, **kwargs):
        """
        1.9 Ensure IAM password policy requires minimum length of 14 or greater (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.password_policy)
        if error:
            if 'NoSuchEntity' in error:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'Password policy does not exist'
                )
            else:
                self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.password_policy)
        if data.get('MinimumPasswordLength') and data.get('MinimumPasswordLength') < 14:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )
        else:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                0,
                'Password policy does not require at least 14 characters'
            )

    @cis_rule('1.10')
    def check_cis_aws_1_10(self, **kwargs):
        """
        1.10 Ensure IAM password policy prevents password reuse (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.password_policy)
        if error:
            if 'NoSuchEntity' in error:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'Password policy does not exist'
                )
            else:
                self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.password_policy)
        if data.get('PasswordReusePrevention') == 24:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )
        else:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                0,
                'Password policy does not prevent reusing last 24 passwords'
            )

    @cis_rule('1.11')
    def check_cis_aws_1_11(self, **kwargs):
        """
        1.11 Ensure IAM password policy expires passwords within 90 days or less (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.password_policy)
        if error:
            if 'NoSuchEntity' in error:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'Password policy does not exist'
                )
            else:
                self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.password_policy)
        if data.get('ExpirePasswords') is True and 0 < data.get('MaxPasswordAge', 0) <= 90:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )
        else:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                0,
                'Password policy does not expire passwords after 90 days or less'
            )

    @cis_rule('1.12')
    def check_cis_aws_1_12(self, **kwargs):
        """
        1.12 Ensure no root account access key exists (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.credential_report)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.credential_report)
        for user in data:
            if user['user'] == '<root_account>':
                access_key_1_active = user.get('access_key_1_active') == 'true'
                access_key_2_active = user.get('access_key_2_active') == 'true'

                if access_key_1_active or access_key_2_active:
                    self.report.add_rule(
                        RuleStatus.Failed,
                        rule_section,
                        (1, 1),
                        1,
                        'Root account has active access keys',
                        {
                            'type': 'users',
                            'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                                     f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                                     f'(data.aws_account_id == "{self.account_id or ""}")])'
                        }
                    )
                else:
                    self.report.add_rule(
                        RuleStatus.Passed,
                        rule_section,
                        (0, 1),
                        0,
                        ''
                    )
                break
        else:
            self.report.add_rule_error(rule_section, 'Could not find the root account in the credentials report')

    @cis_rule('1.13')
    def check_cis_aws_1_13(self, **kwargs):
        """
        1.13 Ensure MFA is enabled for the "root" account (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.account_summary)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.account_summary)
        if data.get('AccountMFAEnabled') != 1 and data.get('AccountMFAEnabled') is not True:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                1,
                'MFA is not enabled for the root account',
                {
                    'type': 'users',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )

    @cis_rule('1.14')
    def check_cis_aws_1_14(self, **kwargs):
        """
        1.14 Ensure hardware MFA is enabled for the "root" account (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.account_summary)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.account_summary)
        if data.get('AccountMFAEnabled') != 1 or data.get('AccountMFAEnabled') is not True:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                1,
                'No MFA (Virtual or Hardware) is enabled for the root account',
                {
                    'type': 'users',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
            return

        # Check if we have hardware mfa
        for page in self.iam_client.get_paginator('list_virtual_mfa_devices').paginate(AssignmentStatus='Any'):
            for virtual_mfa_device in (page.get('VirtualMFADevices') or []):
                if 'mfa/root-account-mfa-device' in str(virtual_mfa_device).lower():
                    self.report.add_rule(
                        RuleStatus.Failed,
                        rule_section,
                        (1, 1),
                        1,
                        'Root account is using virtual MFA',
                        {
                            'type': 'users',
                            'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                                     f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                                     f'(data.aws_account_id == "{self.account_id or ""}")])'
                        }
                    )
                    return

        # If we have reached here, then we have hardware mfa enabled for the root account
        self.report.add_rule(
            RuleStatus.Passed,
            rule_section,
            (0, 1),
            0,
            ''
        )

    @cis_rule('1.16')
    def check_cis_aws_1_16(self, **kwargs):
        """
        1.16 Ensure IAM policies are attached only to groups or roles (Scored)
        """
        rule_section = kwargs['rule_section']

        failed_users = []
        number_of_users = 0
        for list_users_page in self.iam_client.get_paginator('list_users').paginate():
            for user in (list_users_page.get('Users') or []):
                number_of_users += 1
                has_inline_policies = False
                has_direct_policies = False
                if self.iam_client.list_user_policies(UserName=user['UserName'], MaxItems=1).get('PolicyNames'):
                    has_inline_policies = True
                if self.iam_client.list_attached_user_policies(
                        UserName=user['UserName'],
                        MaxItems=1
                ).get('AttachedPolicies'):
                    has_direct_policies = True

                if has_inline_policies and has_direct_policies:
                    failed_users.append(f'User "{user["UserName"]}" ({user["Arn"]}) has both direct and inline '
                                        f'policies attached.')
                elif has_inline_policies:
                    failed_users.append(f'User "{user["UserName"]}" ({user["Arn"]}) has inline policies attached.')
                elif has_direct_policies:
                    failed_users.append(f'User "{user["UserName"]}" ({user["Arn"]}) has direct policies attached.')

        if failed_users:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(failed_users), number_of_users),
                len(failed_users),
                errors_to_gui(failed_users),
                {
                    'type': 'users',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, number_of_users),
                0,
                ''
            )

    @cis_rule('1.20')
    def check_cis_aws_1_20(self, **kwargs):
        rule_section = kwargs['rule_section']
        try:
            policy_exists = False
            for list_policies_page in self.iam_client.get_paginator('list_policies').paginate(
                    Scope='AWS',
                    OnlyAttached=False
            ):
                for policy_object in (list_policies_page.get('Policies') or []):
                    if policy_object.get('PolicyName') == 'AWSSupportAccess':
                        policy_exists = True
                        if policy_object.get('AttachmentCount') and policy_object.get('AttachmentCount') > 0:
                            self.report.add_rule(
                                RuleStatus.Passed,
                                rule_section,
                                (0, 1),
                                0,
                                ''
                            )
                            return

            if policy_exists:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'The policy "AWSSupportAccess" exists but is not attached to any user, group or role'
                )
            else:
                self.report.add_rule(
                    RuleStatus.Failed,
                    rule_section,
                    (1, 1),
                    0,
                    'The policy "AWSSupportAccess" does not exist'
                )
        except Exception as e:
            self.report.add_rule_error(
                rule_section,
                f'Error listing policies (iam.list_policies): {str(e)}'
            )

    @cis_rule('1.22')
    def check_cis_aws_1_22(self, **kwargs):
        """
        1.22 Ensure IAM policies that allow full "*:*" administrative privileges are not created (Scored)
        """
        rule_section = kwargs['rule_section']
        number_of_policies = 0
        policies_errors = []
        for list_policies_page in self.iam_client.get_paginator('list_policies').paginate(
                Scope='Local',
                OnlyAttached=False
        ):
            for policy_object in (list_policies_page.get('Policies') or []):
                number_of_policies += 1
                policy = self.iam_client.get_policy_version(
                    PolicyArn=policy_object['Arn'],
                    VersionId=policy_object['DefaultVersionId']
                )

                statements = []
                if isinstance(policy['PolicyVersion']['Document']['Statement'], list):
                    for statement in policy['PolicyVersion']['Document']['Statement']:
                        statements.append(statement)
                else:
                    statements.append(policy['PolicyVersion']['Document']['Statement'])

                for statement in statements:
                    if 'Action' in statement.keys() and statement.get('Effect') == 'Allow':
                        if ('\'*\'' in str(statement.get('Action')) or str(statement.get('Action')) == '*') and (
                                '\'*\'' in str(statement.get('Resource')) or str(statement.get('Resource')) == '*'):
                            policies_errors.append(f'Policy "{policy.get("PolicyName")}" ({policy.get("Arn")}) '
                                                   f'contains a full "*:*" administrative privilege.')
                            break

        if policies_errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(policies_errors), number_of_policies),
                0,
                errors_to_gui(policies_errors),
                {
                    'type': 'users',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, number_of_policies),
                0,
                ''
            )
