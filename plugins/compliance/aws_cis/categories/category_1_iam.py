"""
Contains all the scored rules for the "IAM" Category of AWS CIS
"""
import csv
import datetime
import logging
import time

import boto3

from axonius.clients.aws.aws_clients import get_boto3_client_by_session
from axonius.utils.datetime import parse_date
from compliance.aws_cis.account_report import AccountReport, RuleStatus
from compliance.aws_cis.aws_cis_utils import bad_api_response, good_api_response, get_api_error, aws_cis_rule, \
    AWS_CIS_DEFAULT_REGION, get_api_data

logger = logging.getLogger(f'axonius.{__name__}')
CREDS_REPORT_DELAY_TIME_IN_SECONDS = 2
MAX_SECONDS_TO_WAIT_FOR_CREDS_REPORT = 60 * 5   # 5 minutes\


# Helper functions
def get_credential_report(iam_client):
    time_slept = 0
    try:
        while iam_client.generate_credential_report()['State'] != 'COMPLETE':
            time.sleep(CREDS_REPORT_DELAY_TIME_IN_SECONDS)
            time_slept += CREDS_REPORT_DELAY_TIME_IN_SECONDS
            if time_slept > MAX_SECONDS_TO_WAIT_FOR_CREDS_REPORT:
                logger.error(f'Error - creds report took more than {CREDS_REPORT_DELAY_TIME_IN_SECONDS} seconds')
                return bad_api_response('Error - timed out generating iam credential report')
        response = iam_client.get_credential_report()
        return good_api_response(list(csv.DictReader(response['Content'].decode('utf-8').splitlines(), delimiter=',')))
    except Exception as e:
        logger.exception(f'Exception while generating credential report')
        return bad_api_response(
            f'Error generating credential report (iam.generate_credential_report, iam.get_credential_report) - {str(e)}'
        )


def get_password_policy(iam_client):
    try:
        policy = iam_client.get_account_password_policy()
        if 'PasswordPolicy' not in policy:
            return ValueError(f'Bad response - can not find "PasswordPolicy" in response')

        return policy['PasswordPolicy']
    except Exception as e:
        logger.exception('Exception while getting account password policy')
        return bad_api_response(f'Error getting account password policy (iam.get_account_password_policy API): '
                                f'{str(e)}')


def get_account_summary(iam_client):
    try:
        summary = iam_client.get_account_summary()
        if 'SummaryMap' not in summary:
            return ValueError(f'Bad response - can not find "SummaryMap" in response')

        return summary['SummaryMap']
    except Exception as e:
        logger.exception('Exception while getting account summary')
        return bad_api_response(f'Error getting account summary (iam.get_account_summary API): '
                                f'{str(e)}')


# Rules
class CISAWSCategory1:
    def __init__(self, report: AccountReport, session: boto3.Session, account_dict: dict):
        self.report = report
        self.account_name = account_dict.get('name') or ''
        self.region_name = account_dict.get('region_name') or AWS_CIS_DEFAULT_REGION
        self.https_proxy = account_dict.get('https_proxy')
        self.iam_client = get_boto3_client_by_session('iam', session, self.region_name, self.https_proxy)
        self.credential_report = get_credential_report(self.iam_client)
        self.password_policy = get_password_policy(self.iam_client)
        self.account_summary = get_account_summary(self.iam_client)

    @aws_cis_rule('1.1')
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
                        f'Access Key 1 been used with password in the last 30 days: {access_key_1_last_used_date}'
                    )
                if access_key_2_last_used_date and access_key_2_last_used_date > a_month_ago:
                    error_messages.append(
                        f'Access Key 2 been used with password in the last 30 days: {access_key_2_last_used_date}'
                    )

                if error_messages:
                    self.report.add_rule(
                        RuleStatus.Failed,
                        rule_section,
                        (1, 1),
                        0,
                        '\n'.join(error_messages)
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
    @aws_cis_rule('1.2')
    def check_cis_aws_1_2(self):
        """
        1.2  Ensure multi-factor authentication (MFA) is enabled for all IAM users that have a console password (scored)
        """
        pass

    @aws_cis_rule('1.3')
    def check_cis_aws_1_3(self):
        """
        1.3  Ensure credentials unused for 90 days or greater are disabled (Scored)
        """
        pass

    @aws_cis_rule('1.4')
    def check_cis_aws_1_4(self):
        """
        1.4 Ensure access keys are rotated every 90 days or less (Scored)
        """
        pass

    @aws_cis_rule('1.5')
    def check_cis_aws_1_5(self):
        """
        1.5 Ensure IAM password policy requires at least one uppercase letter (Scored)
        """
        pass

    @aws_cis_rule('1.6')
    def check_cis_aws_1_6(self):
        """
        1.6 Ensure IAM password policy require at least one lowercase letter (Scored)
        """
        pass

    @aws_cis_rule('1.7')
    def check_cis_aws_1_7(self):
        """
        1.7 Ensure IAM password policy require at least one symbol (Scored)
        """
        pass

    @aws_cis_rule('1.8')
    def check_cis_aws_1_8(self):
        """
        1.8 Ensure IAM password policy require at least one number (Scored)
        """
        pass

    @aws_cis_rule('1.9')
    def check_cis_aws_1_9(self):
        """
        1.9 Ensure IAM password policy requires minimum length of 14 or greater (Scored)
        """
        pass

    @aws_cis_rule('1.10')
    def check_cis_aws_1_10(self):
        """
        1.10 Ensure IAM password policy prevents password reuse (Scored)
        """
        pass

    @aws_cis_rule('1.11')
    def check_cis_aws_1_11(self):
        """
        1.11 Ensure IAM password policy expires passwords within 90 days or less (Scored)
        """
        pass

    @aws_cis_rule('1.12')
    def check_cis_aws_1_12(self):
        """
        1.12 Ensure no root account access key exists (Scored)
        """
        pass

    @aws_cis_rule('1.13')
    def check_cis_aws_1_13(self):
        """
        1.13 Ensure MFA is enabled for the "root" account (Scored)
        """
        pass

    @aws_cis_rule('1.14')
    def check_cis_aws_1_14(self):
        """
        1.14 Ensure hardware MFA is enabled for the "root" account (Scored)
        """
        pass

    @aws_cis_rule('1.16')
    def check_cis_aws_1_16(self):
        """
        1.16 Ensure IAM policies are attached only to groups or roles (Scored)
        """
        pass

    @aws_cis_rule('1.20')
    def check_cis_aws_1_20(self):
        """
        1.20 Ensure a support role has been created to manage incidents with AWS Support (Scored)
        """
        pass

    @aws_cis_rule('1.22')
    def check_cis_aws_1_22(self):
        """
        1.22 Ensure IAM policies that allow full "*:*" administrative privileges are not created (Scored)
        """
        pass
