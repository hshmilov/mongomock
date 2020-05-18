# pylint: disable=too-many-lines,duplicate-code, protected-access
import urllib
import urllib.parse
from datetime import datetime
from typing import List

from axonius.consts.plugin_consts import COMPLIANCE_PLUGIN_NAME
from axonius.plugin_base import PluginBase

from axonius.compliance.aws_cis_default_rules import get_default_cis_aws_compliance_report
from axonius.compliance.azure_cis_default_rules import get_default_cis_azure_compliance_report


def _get_compliance_reports_collection(compliance_name):
    return 'reports' if compliance_name == 'aws' else f'{compliance_name}_reports'


def _get_compliance_default_rules(compliance_name):
    if compliance_name == 'aws':
        return get_default_cis_aws_compliance_report()
    if compliance_name == 'azure':
        return get_default_cis_azure_compliance_report()
    return {}


def get_compliance_accounts(compliance_name):
    # Get all latest account names. Since account_id does not change we can group by it, and this will work
    # even if the account name changed.
    # pylint: disable=protected-access
    compliance_reports_collection = _get_compliance_reports_collection(
        compliance_name)
    reports_db = PluginBase.Instance._get_db_connection(
    )[COMPLIANCE_PLUGIN_NAME][compliance_reports_collection]
    all_account_names = [
        report.get('account_name') for report in
        reports_db.aggregate(
            [
                {
                    '$group': {
                        '_id': '$account_id',
                        'account_name': {'$last': '$account_name'}
                    }
                },
                {
                    '$sort': {'account_name': 1}
                },
            ]
        ) if report.get('account_name')]
    if not all_account_names:
        return []
    return all_account_names


def get_compliance(compliance_name: str, method: str, accounts: list):
    if compliance_name in ['aws', 'azure']:
        if method == 'report':
            return list(get_compliance_rules(accounts, compliance_name))
        if method == 'accounts':
            return get_compliance_accounts(compliance_name)
        if method == 'report_no_data':
            return {
                'status': 'no_data',
                'error': 'Please connect the AWS Adapter',
                'rules': [],
            }

    raise ValueError(f'Data not found')


def get_compliance_rules(accounts, compliance_name) -> List[dict]:
    def beautify_compliance(
            compliance: dict,
            account_id: str,
            account_name: str,
            last_updated: datetime):
        compliance_results = compliance.get('results') or {}
        beautify_object = {
            'id': urllib.parse.quote(
                f'{account_id}__{compliance["section"]}',
                safe=''),
            'status': compliance.get('status'),
            'section': compliance.get('section'),
            'category': compliance.get('category'),
            'account': account_name,
            'results': f'{compliance_results.get("failed", 0)}/{compliance_results.get("checked", 0)}',
            'entities_results': compliance.get('entities_results'),
            'error': compliance.get('error'),
            'affected': compliance.get('affected_entities'),
            'cis': compliance.get('cis'),
            'description': compliance.get('description'),
            'remediation': compliance.get('remediation'),
            'rule': compliance.get('rule_name'),
            'entities_results_query': compliance.get('entities_results_query'),
            'last_updated': last_updated or datetime.now()}
        return beautify_object

    # pylint: disable=protected-access
    compliance_reports_collection = _get_compliance_reports_collection(
        compliance_name)
    all_reports = list(PluginBase.Instance._get_db_connection()[COMPLIANCE_PLUGIN_NAME][compliance_reports_collection]
                       .aggregate([
                           {
                               '$group': {
                                   '_id': '$account_id',
                                   'last': {'$last': '$$ROOT'}
                               }
                           },
                           {
                               '$sort': {'last.account_name': 1},
                           }
                       ]))

    all_accounts = set(accounts)

    if not all_reports:
        default_rules = _get_compliance_default_rules(
            compliance_name).get('rules')
        time_now = datetime.now()
        if len(all_accounts) == 0:
            yield from (beautify_compliance(rule, rule['account'], rule['account'], time_now) for rule in default_rules)
        for account in all_accounts:
            yield from (beautify_compliance(rule, account, account, time_now)
                        for rule in default_rules if rule['account'] == account)

    for report_doc in all_reports:
        report = report_doc['last']
        if len(all_accounts) == 0 or report['account_name'] in all_accounts:
            yield from (beautify_compliance(rule, report['account_id'], report['account_name'], report['last_updated'])
                        for rule in report['report'].get('rules') or [])
