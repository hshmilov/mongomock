"""
Here the actual logic happens
"""
import logging
from collections import defaultdict
from typing import List, Dict

import boto3

from axonius.clients.aws.aws_clients import get_boto3_client_by_session
from axonius.clients.aws.consts import REGIONS_NAMES
from axonius.compliance.aws_cis_consts import AWS_CIS_ALL_RULES
from compliance.aws_cis.account_report import AccountReport
from compliance.aws_cis.aws_cis_utils import good_api_response, bad_api_response
from compliance.aws_cis.categories.category_1_iam import CISAWSCategory1
from compliance.aws_cis.categories.category_2_logging import CISAWSCategory2
from compliance.aws_cis.categories.category_3_monitoring import CISAWSCategory3
from compliance.aws_cis.categories.category_4_networking import CISAWSCategory4

logger = logging.getLogger(f'axonius.{__name__}')


def generate_failed_report(report: AccountReport, error: str):
    for rule_section in AWS_CIS_ALL_RULES:
        report.add_rule_error(rule_section, error)


def get_all_cloudtrails(regions: List[str], session: boto3.Session, https_proxy: str) -> Dict[str, list]:
    trails = defaultdict(list)
    first_exception = None
    did_one_succeed = False
    trail_arn_set = set()
    for region_name in regions:
        try:
            cloudtrail_client = get_boto3_client_by_session('cloudtrail', session, region_name, https_proxy)
            for cloudtrail in (cloudtrail_client.describe_trails().get('trailList') or []):
                if cloudtrail.get('TrailARN') in trail_arn_set:
                    # No reason to add the same trail (happens on MultiRegion trails's)
                    continue
                if cloudtrail.get('IsMultiRegionTrail') is True:
                    region_to_put = cloudtrail.get('HomeRegion') or region_name
                else:
                    region_to_put = region_name

                trail_arn_set.add(cloudtrail.get('TrailARN'))
                trails[region_to_put].append(cloudtrail)
            did_one_succeed = True
        except Exception as e:
            logger.debug(f'CloudTrail: Could not parse region {region_name}', exc_info=True)
            if not first_exception:
                first_exception = e

    if did_one_succeed:
        return good_api_response(trails)

    if 'An error occurred (AccessDeniedException)' not in str(first_exception):
        logger.exception(f'Failed getting cloudtrails')
    return bad_api_response(
        f'Error generating credential report (cloudtrail.describe_trails) - {str(first_exception)}'
    )


# pylint: disable=too-many-statements
def generate_rules(report: AccountReport, session: boto3.Session, account_dict: dict):
    if account_dict.get('region_name') and not account_dict.get('get_all_regions'):
        regions = [account_dict.get('region_name')]
    else:
        regions = REGIONS_NAMES
    cloudtrails = get_all_cloudtrails(regions, session, account_dict.get('https_proxy'))

    category_1 = CISAWSCategory1(report, session, account_dict)
    category_1.check_cis_aws_1_1()
    category_1.check_cis_aws_1_2()
    category_1.check_cis_aws_1_3()
    category_1.check_cis_aws_1_4()
    category_1.check_cis_aws_1_5()
    category_1.check_cis_aws_1_6()
    category_1.check_cis_aws_1_7()
    category_1.check_cis_aws_1_8()
    category_1.check_cis_aws_1_9()
    category_1.check_cis_aws_1_10()
    category_1.check_cis_aws_1_11()
    category_1.check_cis_aws_1_12()
    category_1.check_cis_aws_1_13()
    category_1.check_cis_aws_1_14()
    category_1.check_cis_aws_1_16()
    # category_1.check_cis_aws_1_20()       # Unscored, not needed
    category_1.check_cis_aws_1_22()

    category_2 = CISAWSCategory2(report, session, account_dict, cloudtrails)
    category_2.check_cis_aws_2_1()
    category_2.check_cis_aws_2_2()
    category_2.check_cis_aws_2_3()
    category_2.check_cis_aws_2_4()
    category_2.check_cis_aws_2_5()
    category_2.check_cis_aws_2_6()
    category_2.check_cis_aws_2_7()
    category_2.check_cis_aws_2_8()
    category_2.check_cis_aws_2_9()

    category_3 = CISAWSCategory3(report, session, account_dict, cloudtrails)
    category_3.check_cis_aws_3_1()
    category_3.check_cis_aws_3_2()
    category_3.check_cis_aws_3_3()
    category_3.check_cis_aws_3_4()
    category_3.check_cis_aws_3_5()
    category_3.check_cis_aws_3_6()
    category_3.check_cis_aws_3_7()
    category_3.check_cis_aws_3_8()
    category_3.check_cis_aws_3_9()
    category_3.check_cis_aws_3_10()
    category_3.check_cis_aws_3_11()
    category_3.check_cis_aws_3_12()
    category_3.check_cis_aws_3_13()
    category_3.check_cis_aws_3_14()

    category_4 = CISAWSCategory4(report, session, account_dict)
    category_4.check_cis_aws_4_1()
    category_4.check_cis_aws_4_2()
    category_4.check_cis_aws_4_3()
