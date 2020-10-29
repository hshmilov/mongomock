import json
import logging
import os
from datetime import datetime
import re
import io
from typing import Optional

from flask import (jsonify,
                   make_response, request)

from axonius.compliance.compliance import get_compliance, get_compliance_initial_cis, \
    get_compliance_filters, update_rules_score_flag, update_compliance_comments
from axonius.consts.gui_consts import (FeatureFlagsNames, CloudComplianceNames, FILE_NAME_TIMESTAMP_FORMAT)
from axonius.logging.audit_helper import AuditCategory, AuditAction
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from axonius.plugin_base import return_error, PluginBase
from axonius.utils.gui_helpers import (accounts as accounts_filter,
                                       schema_fields as schema,
                                       rules as rules_filter,
                                       categories as categories_filter,
                                       failed_rules as failed_rules_filter,
                                       rules_for_score as include_rules_in_score,
                                       email_properties, jira_properties, aggregated_view, return_api_format)
from gui.logic.entity_data import (get_export_csv, get_cloud_admin_users)
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in

# pylint: disable=no-member,no-self-use

logger = logging.getLogger(f'axonius.{__name__}')

SAML_SETTINGS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', 'saml_settings.json'))


@gui_category_add_rules('compliance')
class Compliance:

    @gui_route_logged_in('initial_cis', methods=['GET'])
    def get_compliance_info(self):
        """
        path: /api/compliance/initial_cis
        """
        try:
            return jsonify(get_compliance_initial_cis())
        except Exception as e:
            logger.exception(f'Error getting compliance initial data')
            return return_error(str(e), http_status=500)

    @gui_route_logged_in('<name>/filters', methods=['GET'])
    def get_compliance_filters(self, name):
        """
        path: /api/compliance/<name>/filters
        """
        try:
            return jsonify(get_compliance_filters(name))
        except Exception as e:
            logger.exception(f'Error getting compliance initial data')
            return return_error(str(e), http_status=500)

    @include_rules_in_score()
    @gui_route_logged_in('<name>/rules', methods=['POST'], activity_params=['cis_title'])
    def update_compliance_rules(self, name, rules):
        """
        path: /api/compliance/<name>/rules
        """
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
    @return_api_format()
    @gui_route_logged_in('<name>/<method>', methods=['GET', 'POST'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Compliance), skip_activity=True)
    def compliance(self, name, method, accounts, rules, categories, failed_only, aggregated, api_format: bool = True):
        """
        path: /api/compliance/<name>/<method>
        """
        response = self._get_compliance(name, method, accounts, rules, categories, failed_only, aggregated)
        if api_format:
            response_dict = json.loads(response.data)
            return jsonify(response_dict.get('rules', []))
        return response

    def _get_compliance(self, name, method, accounts, rules=None, categories=None, failed_only=False,
                        aggregated=True):
        try:
            if not self._is_compliance_visible():
                return return_error('Cloud asset compliance is not visible', http_status=400)
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
        """
        path: /api/compliance/<name>/csv
        """
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
        # pylint: enable=unsupported-assignment-operation

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
        """
        path: /api/compliance/<name>/send_email
        """
        try:
            if not self._is_compliance_visible():
                return return_error('Cloud asset compliance is not visible', http_status=400)
            return self._send_compliance_email(name, schema_fields, accounts, email_props,
                                               rules, categories, failed_only, aggregated)
        except Exception as e:
            logger.exception(f'Error in send_compliance_email')
            return return_error(str(e), non_prod_error=True)

    @staticmethod
    def _get_account_id(account: str) -> Optional[str]:
        match = re.search(r'\((.+)\)', account)
        if match:
            # If account includes <name> (<id>).
            return match.group(1)
        match = re.match(r'^([\s\d]+)$', account)
        if match:
            # If account includes only the account id.
            return match.group(1)

        return None

    # pylint: disable=too-many-locals
    def _send_compliance_email(self, name, schema_fields, accounts, email_props, rules, categories, failed_only,
                               aggregated):
        if not self.mail_sender:
            logger.error('No mail_sender configured.')
            return return_error('Send Email Failed', http_status=400)
        try:
            # Prepare email props.
            subject = email_props.get('mailSubject', '')
            email_list = email_props.get('emailList') or []
            email_list_cc = email_props.get('emailListCC') or []
            email_text_content = email_props.get('mailMessage', '')
            timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)

            emails_per_account = {}

            if email_props.get('accountAdmins'):
                for account_name in accounts:
                    account_id = self._get_account_id(account_name)
                    if not account_id:
                        logger.critical(f'Could not find account id from account name {account_name}! not sending')
                        continue

                    email_list_admins = get_cloud_admin_users(name, account_id) or []
                    logger.info(f'{name} CIS Admin users for account {account_name} with account_id {account_id}: '
                                f'{str(email_list_admins)}')

                    # if one of the admins are already in emailList, do not send this email again
                    emails_per_account[account_name] = list(set(email_list_admins) - set(email_list))

            if not email_list and not email_list_cc and not emails_per_account:
                logger.error('Can\'t send email to an empty list.')
                return return_error('Send Email Failed', http_status=400)

            # Send to the emailList + emailListCC
            csv_string = self._get_compliance_rules_csv_file(name, schema_fields, accounts,
                                                             rules, categories, failed_only, aggregated)
            email = self.mail_sender.new_email(subject,
                                               email_list,
                                               cc_recipients=email_list_cc)
            email.add_attachment(f'axonius-cloud_{timestamp}.csv', csv_string.getvalue().encode('utf-8'),
                                 'text/csv')
            email.send(email_text_content)

            # Send to the accounts
            for account, emails in emails_per_account.items():
                try:
                    if not emails:
                        continue
                    logger.info(f'Sending cis report for account {account!r} with emails: {emails}')
                    csv_string = self._get_compliance_rules_csv_file(name, schema_fields, [account],
                                                                     rules, categories, failed_only, aggregated)
                    email = self.mail_sender.new_email(subject,
                                                       emails,
                                                       cc_recipients=email_list_cc)
                    email.add_attachment(f'axonius-cloud_{timestamp}.csv', csv_string.getvalue().encode('utf-8'),
                                         'text/csv')
                    email.send(email_text_content)
                except Exception:
                    logger.exception(f'Problem sending compliance email for account {account} to {emails}')

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
        """
        path: /api/compliance/<name>/create_jira
        """
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
        message, permalink = PluginBase.Instance.create_jira_ticket(jira_props.get('project_key'),
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

    @gui_route_logged_in('<name>/comments', methods=['POST', 'PUT', 'DELETE'],
                         required_permission=PermissionValue.get(
                             PermissionAction.Update, PermissionCategory.Compliance, PermissionCategory.Comments),
                         skip_activity=True)
    def api_update_compliance_comments(self, name):
        """
        path: /api/compliance/<name>/comments
        """
        content = self.get_request_data_as_object()
        comment = content.get('comment', {})

        if not self._is_compliance_visible():
            return return_error('Cloud asset compliance is not visible', http_status=400)

        if request.method != 'DELETE' and (not comment.get('text') or not comment.get('account')):
            return return_error('Content of comment & account should not be empty', http_status=400)

        if comment.get('text') and len(comment.get('text')) > 150:
            return return_error('Content of comment cannot exceed 150 characters', http_status=400)

        section = content.get('section')
        index = content.get('index')
        try:
            update_compliance_comments(name, section, comment, index)
        except BaseException:
            errors = {
                'PUT': 'Failed to create comment',
                'POST': 'Failed to edit comment',
                'DELETE': 'Failed to delete comment'
            }
            return return_error(errors[request.method], http_status=500)

        audit_actions = {
            'PUT': AuditAction.AddComment,
            'POST': AuditAction.EditComment,
            'DELETE': AuditAction.DeleteComment
        }
        self.log_activity_user(AuditCategory.Compliance, audit_actions.get(request.method), {
            'section': section,
            'name': name
        })
        return ''
