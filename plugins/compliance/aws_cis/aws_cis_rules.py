"""
Here the actual logic happens
"""
import logging

import boto3

from compliance.aws_cis.account_report import AccountReport
from compliance.aws_cis.categories.category_1_iam import CISAWSCategory1

logger = logging.getLogger(f'axonius.{__name__}')


def generate_rules(report: AccountReport, session: boto3.Session, account_dict: dict):

    # Category 1
    category_1_1 = CISAWSCategory1(report, session, account_dict)
    category_1_1.check_cis_aws_1_1()
