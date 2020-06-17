import logging
import os
from datetime import datetime
import re
import io

from flask import (jsonify,
                   make_response)

from axonius.compliance.compliance import get_compliance, get_compliance_initial_cis,\
    get_compliance_filters, update_rules_score_flag
from axonius.consts.gui_consts import (FeatureFlagsNames, CloudComplianceNames, FILE_NAME_TIMESTAMP_FORMAT)
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from axonius.plugin_base import return_error, PluginBase
from axonius.utils.gui_helpers import (accounts as accounts_filter,
                                       schema_fields as schema,
                                       rules as rules_filter,
                                       categories as categories_filter,
                                       failed_rules as failed_rules_filter,
                                       rules_for_score as include_rules_in_score,
                                       email_properties, jira_properties, aggregated_view)
from gui.logic.entity_data import (get_export_csv, get_cloud_admin_users)
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in

# pylint: disable=no-member,no-self-use

logger = logging.getLogger(f'axonius.{__name__}')

SAML_SETTINGS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', 'saml_settings.json'))


@gui_category_add_rules('compliance')
class Compliance:

    @gui_route_logged_in('initial_cis', methods=['GET'])
    def get_compliance_info(self):

        try:
            return jsonify(get_compliance_initial_cis())
        except Exception as e:
            logger.exception(f'Error getting compliance initial data')
            return return_error(str(e),  http_status=500)

    @gui_route_logged_in('<name>/filters', methods=['GET'])
    def get_compliance_filters(self, name):
        try:
            return jsonify(get_compliance_filters(name))
        except Exception as e:
            logger.exception(f'Error getting compliance initial data')
            return return_error(str(e), http_status=500)

    @include_rules_in_score()
    @gui_route_logged_in('<name>/rules', methods=['POST'], activity_params=['cis_title'])
    def update_compliance_rules(self, name, rules):
        try:
            return jsonify(update_rules_score_flag(name, rules))
        except Exception as e:
            logger.exception(f'Error getting compliance initial data')
            return return_error(str(e), http_status=500)

    @accounts_filter()
    @rules_filter()
    @categories_filter()
    @failed_rules_filter()
    @aggregated_view()
    @gui_route_logged_in('<name>/<method>', methods=['GET', 'POST'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Compliance), skip_activity=True)
    def compliance(self, name, method, accounts, rules, categories, failed_only, aggregated):
        return self._get_compliance(name, method, accounts, rules, categories, failed_only, aggregated)

    def _get_compliance(self, name, method, accounts, rules=None, categories=None, failed_only=False,
                        aggregated=True):
        try:
            if not self._is_compliance_visible():
                return return_error('Cloud asset compliance is not visible',  http_status=400)
            return jsonify(get_compliance(name, method, accounts, rules, categories, failed_only, aggregated))
        except Exception as e:
            logger.exception(f'Error in get_compliance')
            return return_error(str(e), http_status=400)

    @accounts_filter()
    @rules_filter()
    @categories_filter()
    @failed_rules_filter()
    @schema()
    @aggregated_view()
    @gui_route_logged_in('<name>/csv', methods=['POST'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Compliance))
    def compliance_csv(self, name, schema_fields, accounts, rules, categories, failed_only, aggregated):
        return self._post_compliance_csv(name, schema_fields, accounts, rules, categories, failed_only, aggregated)

    @staticmethod
    def _get_compliance_rules_csv_file(compliance_name, schema_fields, accounts, rules, categories, failed_only,
                                       aggregated):
        rules = get_compliance(compliance_name, 'report', accounts, rules, categories, failed_only,
                               aggregated).get('rules', [])

        def _get_order(elem):
            return elem.get('order')

        schema_fields.sort(key=_get_order)

        field_by_name = {
            field['name']: field for field in
            # show only the fields with 0 or more in the order attribute
            list(filter(lambda f: _get_order(f) >= 0, schema_fields))
        }
        # pylint: disable=unsupported-assignment-operation
        for rule in rules:
            rule['entities_results'] = rule.get('error') \
                if rule.get('error') else rule.get('entities_results')
        #pylint: enable=unsupported-assignment-operation

        return get_export_csv(rules, field_by_name, None)

    def _post_compliance_csv(self, name, schema_fields, accounts, rules=None, categories=None, failed_only=False,
                             aggregated=True):
        try:
            if not self._is_compliance_visible():
                return return_error('Cloud asset compliance is not visible', http_status=400)
            return self._get_compliance_rules_csv(name, schema_fields, accounts, rules, categories, failed_only,
                                                  aggregated)
        except Exception as e:
            logger.exception(f'Error in get_compliance')
            return return_error(str(e), non_prod_error=True, http_status=500)

    def _is_compliance_visible(self):
        cloud_compliance_settings = self.feature_flags_config().get(FeatureFlagsNames.CloudCompliance) or {}
        is_cloud_compliance_visible = cloud_compliance_settings.get(CloudComplianceNames.Visible)
        return is_cloud_compliance_visible

    @staticmethod
    def _get_compliance_rules_csv(compliance_name, schema_fields, accounts, rules, categories, failed_only, aggregated):
        csv_string = Compliance._get_compliance_rules_csv_file(compliance_name, schema_fields,
                                                               accounts, rules, categories, failed_only, aggregated)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        output.headers[
            'Content-Disposition'] = f'attachment; filename=axonius-cloud_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @accounts_filter()
    @rules_filter()
    @categories_filter()
    @failed_rules_filter()
    @schema()
    @email_properties()
    @aggregated_view()
    @gui_route_logged_in('<name>/send_email', methods=['POST'], required_permission=PermissionValue.get(
        PermissionAction.Add, PermissionCategory.Enforcements), activity_params=['cis_title'])
    def send_compliance_email(self, name, schema_fields, accounts, email_props, rules, categories, failed_only,
                              aggregated):
        try:
            if not self._is_compliance_visible():
                return return_error('Cloud asset compliance is not visible',  http_status=400)
            return self._send_compliance_email(name, schema_fields, accounts, email_props,
                                               rules, categories, failed_only, aggregated)
        except Exception as e:
            logger.exception(f'Error in send_compliance_email')
            return return_error(str(e), non_prod_error=True)

    @staticmethod
    def _get_account_ids(accounts):
        account_ids = []
        for account_name in accounts:
            match = re.search(r'\((.+)\)', account_name)
            if match:
                # If account includes <name> (<id>).
                account_ids.append(match.group(1))
            match = re.match(r'^([\s\d]+)$', account_name)
            if match:
                # If account includes only the account id.
                account_ids.append(match.group(1))
        return account_ids

    def _send_compliance_email(self, name, schema_fields, accounts, email_props, rules, categories, failed_only,
                               aggregated):
        if not self.mail_sender:
            logger.error('No mail_sender configured.')
            return return_error('Send Email Failed', http_status=400)
        try:
            # Prepare email props.
            subject = email_props.get('mailSubject', '')
            email_list = email_props.get('emailList', [])
            email_list_cc = email_props.get('emailListCC', [])
            email_text_content = email_props.get('mailMessage', '')
            timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)

            if email_props.get('accountAdmins'):
                account_ids = self._get_account_ids(accounts)
                email_list_admins = get_cloud_admin_users(name, account_ids)
                logger.info(f'{name} CIS Admin users: {email_list_admins} for accounts: {account_ids}')
                email_list.extend(email_list_admins)

            if email_list is None or len(email_list) == 0:
                logger.error('Can\'t send email to an empty list.')
                return return_error('Send Email Failed', http_status=400)

            csv_string = self._get_compliance_rules_csv_file(name, schema_fields, accounts,
                                                             rules, categories, failed_only, aggregated)

            email = self.mail_sender.new_email(subject,
                                               email_list,
                                               cc_recipients=email_list_cc)
            email.add_attachment(f'axonius-cloud_{timestamp}.csv', csv_string.getvalue().encode('utf-8'),
                                 'text/csv')
            email.send(email_text_content)

            return 'Email sent.'
        except Exception:
            logger.error(f'Failed to send an Email for "{name}" CAC, with accounts {accounts}')
            raise

    @accounts_filter()
    @rules_filter()
    @categories_filter()
    @failed_rules_filter()
    @schema()
    @jira_properties()
    @aggregated_view()
    @gui_route_logged_in('<name>/create_jira', methods=['POST'], required_permission=PermissionValue.get(
        PermissionAction.Add, PermissionCategory.Enforcements), activity_params=['cis_title'])
    def create_jira_issue(self, name, schema_fields, accounts, jira_props, rules, categories, failed_only, aggregated):
        try:
            if not self._is_compliance_visible():
                return return_error('Cloud asset compliance is not visible', http_status=400)
            return self._create_jira_issue(name, schema_fields, accounts, jira_props, rules, categories, failed_only,
                                           aggregated)
        except Exception as e:
            logger.exception(f'Error in create_jira_issue')
            return return_error(str(e), non_prod_error=True)

    @staticmethod
    def _create_jira_issue(name, schema_fields, accounts, jira_props, rules, categories, failed_only, aggregated):
        csv_string = Compliance._get_compliance_rules_csv_file(name, schema_fields,
                                                               accounts, rules, categories, failed_only, aggregated)
        csv_bytes = io.BytesIO(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        file_name = f'axonius - cloud_{timestamp}.csv'
        message = PluginBase.Instance.create_jira_ticket(jira_props.get('project_key'),
                                                         jira_props.get('incident_title'),
                                                         jira_props.get('incident_description'),
                                                         jira_props.get('issue_type'),
                                                         assignee=jira_props.get('assignee'),
                                                         labels=jira_props.get('labels'),
                                                         components=jira_props.get('components'),
                                                         csv_file_name=file_name,
                                                         csv_bytes=csv_bytes)
        if message:
            return return_error('Creating Jira issue failed', http_status=500)
        return make_response('Jira issue created.', 200)
