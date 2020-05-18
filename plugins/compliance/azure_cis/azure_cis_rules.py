"""
Here the actual logic happens
"""
import logging

from axonius.clients.azure.client import AzureCloudConnection
from axonius.compliance.azure_cis_consts import AZURE_CIS_ALL_RULES
from compliance.azure_cis.categories.category_1_iam import CISAzureCategory1
from compliance.azure_cis.categories.category_2_security_center import CISAzureCategory2
from compliance.azure_cis.categories.category_3_storage import CISAzureCategory3
from compliance.azure_cis.categories.category_4_database import CISAzureCategory4
from compliance.azure_cis.categories.category_5_logging import CISAzureCategory5
from compliance.azure_cis.categories.category_6_networking import CISAzureCategory6
from compliance.azure_cis.categories.category_7_virtual_machines import CISAzureCategory7
from compliance.azure_cis.categories.category_8_other import CISAzureCategory8
from compliance.azure_cis.categories.category_9_app_service import CISAzureCategory9
from compliance.utils import AzureAccountReport
from compliance.utils.account_report import AccountReport

logger = logging.getLogger(f'axonius.{__name__}')


def generate_failed_report(report: AccountReport, error: str):
    for rule_section in AZURE_CIS_ALL_RULES:
        report.add_rule_error(rule_section, error)


# pylint: disable=too-many-statements
def generate_rules(report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
    with azure:
        category_1 = CISAzureCategory1(report, azure, account_dict)
        category_1.check_cis_azure_1_3()
        category_1.check_cis_azure_1_23()

        category_2 = CISAzureCategory2(report, azure, account_dict)
        category_2.check_cis_azure_2_1()
        category_2.check_cis_azure_2_2()
        category_2.check_cis_azure_2_3()
        category_2.check_cis_azure_2_4()
        category_2.check_cis_azure_2_5()
        category_2.check_cis_azure_2_6()
        category_2.check_cis_azure_2_7()
        category_2.check_cis_azure_2_8()
        category_2.check_cis_azure_2_9()
        category_2.check_cis_azure_2_10()
        category_2.check_cis_azure_2_11()
        category_2.check_cis_azure_2_12()
        category_2.check_cis_azure_2_13()
        category_2.check_cis_azure_2_14()
        category_2.check_cis_azure_2_15()
        category_2.check_cis_azure_2_16()
        category_2.check_cis_azure_2_17()
        category_2.check_cis_azure_2_18()
        category_2.check_cis_azure_2_19()

        category_3 = CISAzureCategory3(report, azure, account_dict)
        category_3.check_cis_azure_3_1()
        category_3.check_cis_azure_3_6()
        category_3.check_cis_azure_3_7()

        category_4 = CISAzureCategory4(report, azure, account_dict)
        category_4.check_cis_azure_4_1()
        category_4.check_cis_azure_4_2()
        category_4.check_cis_azure_4_3()
        category_4.check_cis_azure_4_4()
        category_4.check_cis_azure_4_5()
        category_4.check_cis_azure_4_6()
        category_4.check_cis_azure_4_7()
        category_4.check_cis_azure_4_8()
        category_4.check_cis_azure_4_9()
        category_4.check_cis_azure_4_10()
        category_4.check_cis_azure_4_11()
        category_4.check_cis_azure_4_12()
        category_4.check_cis_azure_4_13()
        category_4.check_cis_azure_4_14()
        category_4.check_cis_azure_4_15()
        category_4.check_cis_azure_4_16()
        category_4.check_cis_azure_4_17()
        category_4.check_cis_azure_4_18()
        category_4.check_cis_azure_4_19()

        category_5 = CISAzureCategory5(report, azure, account_dict)
        category_5.check_cis_azure_5_1_1()
        category_5.check_cis_azure_5_1_2()
        category_5.check_cis_azure_5_1_3()
        category_5.check_cis_azure_5_1_4()
        category_5.check_cis_azure_5_1_5()
        category_5.check_cis_azure_5_1_6()
        category_5.check_cis_azure_5_1_7()
        category_5.check_cis_azure_5_2_1()
        category_5.check_cis_azure_5_2_2()
        category_5.check_cis_azure_5_2_3()
        category_5.check_cis_azure_5_2_4()
        category_5.check_cis_azure_5_2_5()
        category_5.check_cis_azure_5_2_6()
        category_5.check_cis_azure_5_2_7()
        category_5.check_cis_azure_5_2_8()
        category_5.check_cis_azure_5_2_9()

        category_6 = CISAzureCategory6(report, azure, account_dict)
        category_6.check_cis_azure_6_1()
        category_6.check_cis_azure_6_2()
        category_6.check_cis_azure_6_3()
        category_6.check_cis_azure_6_4()
        category_6.check_cis_azure_6_5()

        category_7 = CISAzureCategory7(report, azure, account_dict)
        category_7.check_cis_azure_7_1()
        category_7.check_cis_azure_7_2()
        category_7.check_cis_azure_7_3()

        category_8 = CISAzureCategory8(report, azure, account_dict)
        category_8.check_cis_azure_8_1()
        category_8.check_cis_azure_8_2()
        category_8.check_cis_azure_8_4()
        category_8.check_cis_azure_8_5()

        category_9 = CISAzureCategory9(report, azure, account_dict)
        category_9.check_cis_azure_9_1()
        category_9.check_cis_azure_9_2()
        category_9.check_cis_azure_9_3()
        category_9.check_cis_azure_9_4()
        category_9.check_cis_azure_9_5()
