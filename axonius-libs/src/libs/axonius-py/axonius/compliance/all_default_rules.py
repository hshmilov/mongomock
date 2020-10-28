# Anyone creating a compliance default rule should add it here
# Import it and add it to the dictionary
# Also add the compliance module name in compliance_consts.py
from typing import Dict, Callable

from axonius.compliance.aws_cis_default_rules import \
    get_default_cis_aws_compliance_report
from axonius.compliance.azure_cis_default_rules import \
    get_default_cis_azure_compliance_report
from axonius.compliance.oracle_cloud_cis_default_rules import \
    get_default_cis_oracle_cloud_compliance_report

ALL_DEFAULT_CIS_REPORTS: Dict[str, Callable[[], Dict]] = {
    'aws': get_default_cis_aws_compliance_report,
    'azure': get_default_cis_azure_compliance_report,
    'oracle_cloud': get_default_cis_oracle_cloud_compliance_report,
}
