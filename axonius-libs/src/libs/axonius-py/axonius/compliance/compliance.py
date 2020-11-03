# pylint: disable=too-many-lines,duplicate-code
# pylint: disable=protected-access
import logging
import re
import urllib
import urllib.parse
from datetime import datetime
from typing import List

from flask import request
from pymongo import UpdateOne

from axonius.compliance.all_default_rules import ALL_DEFAULT_CIS_REPORTS
from axonius.consts import adapter_consts
from axonius.consts.compliance_consts import COMPLIANCE_RULES_COLLECTIONS, COMPLIANCE_MODULES, \
    COMPLIANCE_REPORTS_COLLECTIONS
from axonius.consts.gui_consts import LAST_UPDATED_FIELD
from axonius.consts.plugin_consts import COMPLIANCE_PLUGIN_NAME
from axonius.plugin_base import PluginBase

logger = logging.getLogger(f'axonius.{__name__}')


def _get_compliance_reports_collection(compliance_name):
    reports_collection_name = COMPLIANCE_REPORTS_COLLECTIONS[compliance_name]
    return PluginBase.Instance._get_db_connection()[COMPLIANCE_PLUGIN_NAME][reports_collection_name]


def get_compliance_rules_collection(compliance_name):
    collection_name = COMPLIANCE_RULES_COLLECTIONS[compliance_name]
    return PluginBase.Instance._get_db_connection()[COMPLIANCE_PLUGIN_NAME][collection_name]


def get_compliance_default_rules(compliance_name):
    get_report_func = ALL_DEFAULT_CIS_REPORTS.get(compliance_name)
    if get_report_func and callable(get_report_func):
        return get_report_func()
    logger.warning(f'Unknown compliance name for default rules: {compliance_name}')
    return {}


def get_compliance_accounts(compliance_name):
    # Get all latest account names. Since account_id does not change we can group by it, and this will work
    # even if the account name changed.
    reports_db = _get_compliance_reports_collection(
        compliance_name)
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
    :param compliance_name:  Name of the compliance module (example: 'aws'). One of `COMPLIANCE_MODULES`
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
    :param compliance_name: Name of the compliance module (example: 'aws'). One of `COMPLIANCE_MODULES`
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
    :param compliance_name: Name of the compliance module (example: 'aws'). One of `COMPLIANCE_MODULES`
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


def get_compliance(compliance_name: str, method: str, accounts: list, rules: list, categories: list, failed_only: bool,
                   aggregated: bool):
    """
    Get compliance report info.
    :param compliance_name: Name of the compliance module (example: 'aws'). One of `COMPLIANCE_MODULES`
    :param method: report
    :param accounts: accounts to filter
    :param rules: rules to filter
    :param categories: categories to filter
    :param failed_only: filter failed only rules or not.
    :param aggregated: show aggregated data for accounts or not.
    :return: report info - array of rules.
    """
    if compliance_name in COMPLIANCE_MODULES:
        if method == 'report':
            cis_rules, score = get_compliance_rules(compliance_name, accounts, rules, categories, failed_only,
                                                    aggregated)
            return {
                'rules': list(cis_rules),
                'score': score,
            }
        if method == 'report_no_data':
            pretty_name = ' '.join([x.capitalize() for x in compliance_name.replace('_', ' ').split()])
            return {
                'status': 'no_data',
                'error': f'Please connect {pretty_name} adapter',
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


def is_module_active(active_adapters, module_name):
    for adapter_name in active_adapters:
        if module_name in adapter_name:
            return True
    return False


def get_initial_cis_selection():
    """
    return the initial cis selection.
    :return: The first module name that has a matching adapter configured,
        or 'aws' if no match found.
    :rtype: str
    """
    active_adapters = [adapter.get('plugin_name', '') for adapter in get_active_adapters()]
    for module_name in COMPLIANCE_MODULES:
        if is_module_active(active_adapters, module_name):
            return module_name
    return 'aws'


def get_compliance_initial_cis():
    return {
        'cis': get_initial_cis_selection()
    }


def get_rules_map(compliance_name: str):
    """
    return map of <rule_name, <include_in_score, comments>>
    :param compliance_name: Name of the compliance module (example: 'aws'). One of `COMPLIANCE_MODULES`
    """
    rules_collection = get_compliance_rules_collection(compliance_name)

    rules = rules_collection.find({})
    result = {}

    for rule in rules:
        result[rule.get('rule_name')] = {
            'include_in_score': rule.get('include_in_score', True),
            'comments': rule.get('comments', [])
        }
    return result


def aggregate_reports(accounts_reports, compliance_name):
    rules_dict = {}  # using rules dictionary for fast search.
    accounts_names = set()
    accounts_ids = set()
    last_updated = []
    for report_doc in accounts_reports:
        try:
            report = report_doc['last']
            accounts_ids.add(_get_account_id(report['account_name']))
            accounts_names.add(report['account_name'])
            last_updated.append(report[LAST_UPDATED_FIELD])

            report_rules = report['report'].get('rules')
            for rule in report_rules:
                rule_key = f'{rule.get("section")} {rule.get("rule_name")}'
                existing_rule_object = rules_dict.get(rule_key)
                if not existing_rule_object:
                    rules_dict[rule_key] = rule
                    continue
                _concat_rules_results(existing_rule_object, rule)
        except Exception:
            logger.warning(f'Error while processing report: {report}')
            continue

    aggregated_rules = rules_dict.values()
    _replace_entities_results_query(aggregated_rules, accounts_ids, compliance_name)
    last_updated.sort()
    return aggregated_rules, list(accounts_ids), list(accounts_names), last_updated.pop()


def _concat_rules_results(target_rule, secondary_rule):
    if target_rule.get('status') != 'Failed' and secondary_rule.get('status') != 'Passed':
        target_rule['status'] = 'Failed'

    target_rule_results = target_rule.get('results')
    if not target_rule_results:
        return
    secondary_rule_results = secondary_rule.get('results', {}) or {} if secondary_rule else {}
    if not secondary_rule_results:
        return
    target_rule_results['failed'] = target_rule_results.get('failed', 0) + secondary_rule_results.get('failed', 0)
    target_rule_results['checked'] = target_rule_results.get('checked', 0) + secondary_rule_results.get('checked', 0)

    target_rule['affected_entities'] = target_rule.get('affected_entities') + \
        secondary_rule.get('affected_entities', '')
    target_rule['entities_results'] = f'{target_rule.get("entities_results")}' \
                                      f'\n{secondary_rule.get("entities_results")}' \
        if target_rule.get('entities_results') else secondary_rule.get('entities_results')


def _replace_entities_results_query(aggregated_rules, accounts_ids, compliance_name):
    """
    This function aggregates the affected assets query for each rule in ``compliance_name``.
    :param aggregated_rules: [{rule1}, {rule2} ... ]
    :param accounts_ids: {accounts_id1, account_id2 ...} This is a set of unique ids.
    :param compliance_name: Name of the compliance module (example: 'aws'). One of `COMPLIANCE_MODULES`
    :return:
    """
    account_id_field = f'data.{compliance_name}_account_id'
    for rule in aggregated_rules:
        entities_results_query = rule.get('entities_results_query', {}).get('query')
        if not entities_results_query:
            continue

        new_entities_results_query = f'({account_id_field} in {list(accounts_ids)})'
        # Modified regex to support different account ids by checking for alphanumeric+underscore+dash
        replaced_query = re.sub(fr'\(({account_id_field} == \"[\sA-Za-z0-9_-]+\")\)',
                                new_entities_results_query, entities_results_query)
        rule['entities_results_query']['query'] = replaced_query


def _build_aggregation_query(accounts):
    aggregation_query = [
        {
            '$match': {
                'report.rules': {
                    '$exists': True, '$ne': []
                }
            }
        },
        {
            '$group': {
                '_id': '$account_id',
                'last': {'$last': '$$ROOT'}
            }
        },
        {
            '$group': {
                '_id': '$last.account_name',
                'last': {'$last': '$$ROOT.last'}
            }
        },
        {
            '$sort': {'last.account_name': 1},
        }
    ]

    if len(accounts) > 0:
        return [{'$match': {'account_name': {'$in': accounts}}}, *aggregation_query]
    return aggregation_query


def get_comments_for_csv(comment_list: list):
    if comment_list:
        return [f'{comment["text"]} ({comment["account"]})' for comment in comment_list]
    return []


def _beautify_compliance(
        compliance: dict,
        account_id: str,
        account_name: list,
        last_updated: datetime,
        rules_map: dict):
    compliance_results = compliance.get('results') or {}

    all_comments = rules_map.get(compliance.get('rule_name')).get('comments', [])
    comments_accounts = account_name + ['All']
    filtered_comments = [item for item in all_comments if item['account'] in comments_accounts]

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
        LAST_UPDATED_FIELD: last_updated or datetime.now(),
        'include_in_score': rules_map.get(compliance.get('rule_name')).get('include_in_score', True),
        'comments': filtered_comments,
        'comments_csv': get_comments_for_csv(filtered_comments)
    }

    return beautify_object


def _matching_rule(rule, rules):
    return len(rules) == 0 or f'{rule.get("section")} {rule.get("rule_name")}' in rules


def _matching_category(rule, categories):
    return len(categories) == 0 or rule.get('category') in categories


def _matching_failed_filter(rule, failed_only):
    return not failed_only or rule.get('status') == 'Failed'


def _filter_rules(compliance_checked_rules, rules_score_flag_map, rules, categories, failed_only):
    return [checked_rule for checked_rule in compliance_checked_rules if
            _matching_rule(checked_rule, rules)
            and _matching_category(checked_rule, categories)
            and _matching_failed_filter(checked_rule, failed_only)
            and rules_score_flag_map.get(checked_rule.get('rule_name'), True)]


def _get_account_id(account_name):
    match = re.search(r'\((.+)\)', account_name)
    if match:
        # If account includes <name> (<id>).
        return match.group(1)
    match = re.match(r'^([\s\d]+)$', account_name)
    if match:
        # If account includes only the account id.
        return match.group(1)
    return account_name


def _calculate_score(reports, rules_score_flag_map):
    # Score calculation is done for ALL rules, without filtering.
    # The only filter that affect score, is the accounts filter. (If we choose specific accounts to get the reports
    # for.

    def is_failed_rule(status):
        return status in ['Failed', 'No Data']

    total_failed = 0
    total_checked = 0
    for report_doc in reports:
        report = report_doc['last']
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


# pylint: disable=too-many-locals
def get_compliance_rules(compliance_name, accounts, rules, categories, failed_only, aggregated) -> List[dict]:
    if rules is None:
        rules = []
    if categories is None:
        categories = []

    all_accounts = set(accounts)
    compliance_reports_collection = _get_compliance_reports_collection(
        compliance_name)
    all_reports = list(compliance_reports_collection
                       .aggregate(_build_aggregation_query(accounts)))

    rules_map = get_rules_map(compliance_name)
    rules_score_flag_map = {rule: rules_map[rule]['include_in_score'] for rule in rules_map}

    def prepare_default_report(default_rules, time_now):
        time_now = datetime.now()
        if len(all_accounts) == 0:
            yield from (_beautify_compliance(rule, rule['account'], [rule['account']], time_now, rules_map)
                        for rule in _filter_rules(default_rules, rules_score_flag_map, rules, categories, failed_only))
        for account in all_accounts:
            yield from (_beautify_compliance(rule, account, [account], time_now, rules_map)
                        for rule in _filter_rules(default_rules, rules_score_flag_map, rules, categories, failed_only)
                        if rule['account'] == account)

    def prepare_report(reports):
        for report_doc in reports:
            report = report_doc['last']
            yield from (_beautify_compliance(rule, report['account_id'], [report['account_name']],
                                             report[LAST_UPDATED_FIELD], rules_map)
                        for rule in _filter_rules(report['report'].get('rules'), rules_score_flag_map, rules,
                                                  categories, failed_only) or [])

    def prepare_aggregated_report(aggregated_rules, accounts_ids, accounts_names, last_updated_report):
        yield from (_beautify_compliance(rule, ','.join(accounts_ids), accounts_names,
                                         last_updated_report, rules_map)
                    for rule in _filter_rules(aggregated_rules, rules_score_flag_map, rules,
                                              categories, failed_only) or [])

    def return_default_report():
        time_now = datetime.now()
        cis_report = prepare_default_report(get_compliance_default_rules(compliance_name).get('rules'), time_now)
        return cis_report, 100

    if not all_reports:
        return return_default_report()

    cis_report = list(prepare_report(all_reports))

    if not cis_report or len(cis_report) == 0:
        # If the the rules array is empty somehow, return the default rules.
        return return_default_report()

    if aggregated:
        aggregated_rules, account_ids, account_names, last_updated = aggregate_reports(all_reports, compliance_name)
        cis_report = prepare_aggregated_report(aggregated_rules, account_ids, account_names, last_updated)
    else:
        cis_report = prepare_report(all_reports)

    score = _calculate_score(all_reports, rules_score_flag_map)
    return cis_report, score


def update_compliance_comments(compliance_name, section, comment, index):
    rules_db = get_compliance_rules_collection(compliance_name)

    find = {'section': section}

    if request.method == 'PUT':
        rules_db.update_one(
            find,
            {
                '$push': {
                    'comments': {
                        '$each': [comment],
                        '$position': 0
                    }
                }
            })
    elif request.method == 'POST':

        rules_db.update_one(
            find,
            {
                '$set':
                    {
                        f'comments.{index}.text': comment.get('text'),
                        f'comments.{index}.account': comment.get('account')
                    }
            })
    else:
        rules_db.update_one(
            find,
            {'$unset': {f'comments.{index}': 1}}
        )
        rules_db.update_one(
            find,
            {'$pull': {'comments': None}}
        )
