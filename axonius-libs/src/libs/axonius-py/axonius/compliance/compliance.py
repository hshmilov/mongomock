# pylint: disable=too-many-lines,duplicate-code
# pylint: disable=protected-access
import urllib
import urllib.parse
from datetime import datetime
from typing import List
from pymongo import UpdateOne

from axonius.compliance.aws_cis_default_rules import get_default_cis_aws_compliance_report
from axonius.compliance.azure_cis_default_rules import get_default_cis_azure_compliance_report
from axonius.consts import adapter_consts
from axonius.consts.plugin_consts import COMPLIANCE_PLUGIN_NAME
from axonius.plugin_base import PluginBase
from axonius.consts.compliance_consts import COMPLIANCE_AWS_RULES_COLLECTION, COMPLIANCE_AZURE_RULES_COLLECTION


def _get_compliance_reports_collection(compliance_name):
    return 'reports' if compliance_name == 'aws' else f'{compliance_name}_reports'


def get_compliance_rules_collection(compliance_name):
    collection_name = COMPLIANCE_AWS_RULES_COLLECTION if compliance_name == 'aws' else COMPLIANCE_AZURE_RULES_COLLECTION
    return PluginBase.Instance._get_db_connection()[COMPLIANCE_PLUGIN_NAME][collection_name]


def get_compliance_default_rules(compliance_name):
    if compliance_name == 'aws':
        return get_default_cis_aws_compliance_report()
    if compliance_name == 'azure':
        return get_default_cis_azure_compliance_report()
    return {}


def get_compliance_accounts(compliance_name):
    # Get all latest account names. Since account_id does not change we can group by it, and this will work
    # even if the account name changed.
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


def get_compliance_rules_info(compliance_name: str):
    """
    Get all existing rules info.
    :param compliance_name:  aws or azure.
    :return: list of rules objects.
    """
    report_rules_db = get_compliance_rules_collection(compliance_name)
    rules_info = list(report_rules_db.aggregate(
        [
            {
                '$group': {
                    '_id': {
                        'rule_name': '$rule_name',
                        'section': '$section',
                        'category': '$category',
                        'include_in_score': '$include_in_score'
                    }
                }
            },
            {
                '$sort': {
                    '_id.section': 1
                }
            }
        ]
    ))

    rules = []
    for item in rules_info:
        rule = item.get('_id')
        if rule:
            rules.append({
                'name': rule.get('rule_name'),
                'section': rule.get('section'),
                'include_in_score': rule.get('include_in_score', True),
                'category': rule.get('category', True),
            })
    return rules


def get_compliance_filters(compliance_name: str):
    """
    Get table filters and rules info.
    :param compliance_name: aws or azure.
    """
    accounts = get_compliance_accounts(compliance_name)
    rules = get_compliance_rules_info(compliance_name)
    return {
        'accounts': accounts,
        'rules': rules,
    }


def update_rules_score_flag(compliance_name: str, rules_map: dict):
    """
    Update the include_in_score flag in db for every rule.
    :param compliance_name: aws or azure
    :param rules_map: dict<rule, boolean>
    :return: None
    """
    rules_collection = get_compliance_rules_collection(compliance_name)

    rules_bulk_update = []
    for rule in rules_map:
        rules_bulk_update.append(UpdateOne(
            {
                'rule_name': rule
            },
            {
                '$set': {
                    'include_in_score': rules_map.get(rule, True)
                }
            }))

    # Update base rules.
    rules_collection.bulk_write(rules_bulk_update)


def get_compliance(compliance_name: str, method: str, accounts: list, rules: list, categories: list, failed_only):
    """
    Get compliance report info.
    :param compliance_name: aws or azure
    :param method: report
    :param accounts: accounts to filter
    :param rules: rules to filter
    :param categories: categories to filter
    :param failed_only: filter failed only rules or not.
    :return: report info - array of rules.
    """
    if compliance_name in ['aws', 'azure']:
        if method == 'report':
            cis_rules, score = get_compliance_rules(compliance_name, accounts, rules, categories, failed_only)
            return {
                'rules': list(cis_rules),
                'score': score,
            }
        if method == 'report_no_data':
            return {
                'status': 'no_data',
                'error': 'Please connect the AWS/Azure Adapter',
                'rules': [],
            }

    raise ValueError(f'Data not found')


def get_active_adapters():
    # get all registered adapters from core
    return PluginBase.Instance.core_configs_collection.find({
        'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
        'hidden': {
            '$ne': True
        },
        'status': 'up'
    }, projection={'plugin_name': 1})


def get_initial_cis_selection():
    """
    return the initial cis selection.
    :return: aws or azure
    """
    active_adapters = get_active_adapters()
    aws_adapter_found = False
    azure_adapter_found = False

    for adapter in active_adapters:
        adapter_name = adapter.get('name', '')
        if 'aws' in adapter_name:
            aws_adapter_found = True
        elif 'azure' in adapter_name:
            azure_adapter_found = True
    if aws_adapter_found or not azure_adapter_found:
        return 'aws'
    return 'azure'


def get_compliance_initial_cis():
    return {
        'cis': get_initial_cis_selection()
    }


def get_compliance_rules_include_score_flag(compliance_name: str):
    """
    return map of <rule_name, include_in_score>
    :param compliance_name: aws or azure
    """
    rules_collection = get_compliance_rules_collection(compliance_name)

    rules = rules_collection.find({})
    result = {}
    for rule in rules:
        result[rule.get('rule_name')] = rule.get('include_in_score', True)
    return result


def get_compliance_rules(compliance_name, accounts, rules, categories, failed_only) -> List[dict]:
    def beautify_compliance(
            compliance: dict,
            account_id: str,
            account_name: str,
            last_updated: datetime,
            rules_score_flag_map: dict):
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
            'last_updated': last_updated or datetime.now(),
            'include_in_score': rules_score_flag_map.get(compliance.get('rule_name'), True)}
        return beautify_object

    def matching_rule(rule):
        return len(rules) == 0 or f'{rule.get("section")} {rule.get("rule_name")}' in rules

    def matching_category(rule):
        return len(categories) == 0 or rule.get('category') in categories

    def matching_failed_filter(rule):
        return not failed_only or rule.get('status') == 'Failed'

    def filter_rules(compliance_checked_rules, rules_score_flag_map):
        return [checked_rule for checked_rule in compliance_checked_rules if
                matching_rule(checked_rule)
                and matching_category(checked_rule)
                and matching_failed_filter(checked_rule)
                and rules_score_flag_map.get(checked_rule.get('rule_name'), True)]

    if rules is None:
        rules = []
    if categories is None:
        categories = []

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
    rules_score_flag_map = get_compliance_rules_include_score_flag(compliance_name)

    def prepare_default_report(default_rules):
        if len(all_accounts) == 0:
            yield from (beautify_compliance(rule, rule['account'], rule['account'], time_now, rules_score_flag_map)
                        for rule in filter_rules(default_rules, rules_score_flag_map))
        for account in all_accounts:
            yield from (beautify_compliance(rule, account, account, time_now, rules_score_flag_map)
                        for rule in filter_rules(default_rules, rules_score_flag_map) if rule['account'] == account)

    def prepare_report(reports):
        for report_doc in reports:
            report = report_doc['last']
            if len(all_accounts) == 0 or report['account_name'] in all_accounts:
                yield from (beautify_compliance(rule, report['account_id'], report['account_name'],
                                                report['last_updated'], rules_score_flag_map)
                            for rule in filter_rules(report['report'].get('rules'), rules_score_flag_map) or [])

    def calculate_score(reports):
        # Score calculation is done for ALL rules, without filtering.
        # The only filter that affect score, is the accounts filter. (If we choose specific accounts to get the reports
        # for.

        def is_failed_rule(status):
            return status in ['Failed', 'No Data']

        total_failed = 0
        total_checked = 0
        for report_doc in reports:
            report = report_doc['last']
            if len(all_accounts) != 0 and report['account_name'] not in all_accounts:
                continue
            cis_rules = report['report'].get('rules', [])
            for rule in cis_rules:
                include_rule = rules_score_flag_map.get(rule.get('rule_name'), True)
                if not include_rule:
                    continue
                if is_failed_rule(rule.get('status')):
                    total_failed += 1
                total_checked += 1
            total_passed = total_checked - total_failed
        if total_checked == 0:
            return 0
        return round((total_passed / total_checked) * 100)

    if not all_reports:
        time_now = datetime.now()
        cis_report = prepare_default_report(get_compliance_default_rules(compliance_name).get('rules'))
        return cis_report, 100

    cis_report = prepare_report(all_reports)
    score = calculate_score(all_reports)
    return cis_report, score
