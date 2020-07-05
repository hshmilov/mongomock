import json
import re
import time

import requests
from test_credentials.test_gui_credentials import DEFAULT_USER

#pylint: disable=line-too-long
NEW_SETTINGS = json.loads('{"aggregation_settings":{"max_workers":20,"socket_read_timeout":5,"uppercase_hostnames":false},"aws_s3_settings":{"aws_access_key_id":null,"aws_secret_access_key":null,"bucket_name":null,"enable_backups":false,"enabled":false,"preshared_key":null},"correlation_schedule":{"correlation_hours_interval":8,"enabled":false},"correlation_settings":{"correlate_ad_sccm":false,"correlate_azure_ad_name_only":false,"correlate_by_ad_display_name":true,"correlate_by_email_prefix":false,"correlate_by_snow_mac":false,"correlate_by_username_domain_only":false,"csv_full_hostname":false},"email_settings":{"ca_file":null,"cert_file":null,"enabled":false,"private_key":null,"sender_address":null,"smtpHost":null,"smtpPassword":null,"smtpPort":null,"smtpUser":null,"use_ssl":"Unencrypted"},"getting_started_checklist":{"enabled":false},"global_ssl":{"cert_file":null,"enabled":false,"hostname":null,"passphrase":[],"private_key":null},"https_log_settings":{"enabled":false,"https_log_port":443,"https_log_server":null,"https_proxy":null},"jira_settings":{"domain":null,"enabled":false,"password":null,"username":null,"verify_ssl":false},"notifications_settings":{"adapter_errors_mail_address":null,"adapters_webhook_address":null},"opsgenie_settings":{"apikey":null,"domain":"https://api.opsgenie.com/","enabled":false,"verify_ssl":false},"password_brute_force_protection":{"conditional":"password_protection_by_ip","enabled":true,"password_lockout_minutes":3,"password_max_allowed_tries":5},"password_policy_settings":{"enabled":false,"password_length":10,"password_min_lowercase":1,"password_min_numbers":1,"password_min_special_chars":0,"password_min_uppercase":1},"proxy_settings":{"enabled":false,"proxy_addr":"","proxy_password":"","proxy_port":8080,"proxy_user":"","proxy_verify":true},"ssl_trust_settings":{"ca_files":[],"enabled":false},"static_analysis_settings":{"fetch_empty_vendor_software_vulnerabilites":false},"syslog_settings":{"ca_file":null,"cert_file":null,"enabled":false,"private_key":null,"syslogHost":null,"syslogPort":514,"use_ssl":"Unencrypted"},"vault_settings":{"application_id":null,"certificate_key":null,"domain":null,"enabled":false,"port":null}}')
OLD_SETTINGS = json.loads('{"aggregation_settings":{"max_workers":20,"socket_read_timeout":5,"uppercase_hostnames":false},"aws_s3_settings":{"aws_access_key_id":null,"aws_secret_access_key":null,"bucket_name":null,"enable_backups":false,"enabled":false,"preshared_key":null},"correlation_schedule":{"correlation_hours_interval":8,"enabled":false},"correlation_settings":{"correlate_ad_sccm":false,"correlate_azure_ad_name_only":false,"correlate_by_ad_display_name":true,"correlate_by_email_prefix":false,"correlate_by_snow_mac":false,"correlate_by_username_domain_only":false,"csv_full_hostname":false},"email_settings":{"ca_file":null,"cert_file":null,"enabled":false,"private_key":null,"sender_address":null,"smtpHost":null,"smtpPassword":null,"smtpPort":null,"smtpUser":null,"use_ssl":"Unencrypted"},"getting_started_checklist":{"enabled":false},"global_ssl":{"cert_file":null,"enabled":false,"hostname":null,"passphrase":[],"private_key":null},"https_log_settings":{"enabled":false,"https_log_port":443,"https_log_server":null,"https_proxy":null},"jira_settings":{"domain":null,"enabled":false,"password":null,"username":null,"verify_ssl":false},"notifications_settings":{"adapter_errors_mail_address":null,"adapters_webhook_address":null},"opsgenie_settings":{"apikey":null,"domain":"https://api.opsgenie.com/","enabled":false,"verify_ssl":false},"password_brute_force_protection":{"conditional":"password_protection_by_ip","enabled":false,"password_lockout_minutes":10,"password_max_allowed_tries":5},"password_policy_settings":{"enabled":false,"password_length":10,"password_min_lowercase":1,"password_min_numbers":1,"password_min_special_chars":0,"password_min_uppercase":1},"proxy_settings":{"enabled":false,"proxy_addr":"","proxy_password":"","proxy_port":8080,"proxy_user":"","proxy_verify":true},"ssl_trust_settings":{"ca_files":[],"enabled":false},"static_analysis_settings":{"fetch_empty_vendor_software_vulnerabilites":false},"syslog_settings":{"ca_file":null,"cert_file":null,"enabled":false,"private_key":null,"syslogHost":null,"syslogPort":514,"use_ssl":"Unencrypted"},"vault_settings":{"application_id":null,"certificate_key":null,"domain":null,"enabled":false,"port":null}}')


def do_login():
    return requests.post('https://127.0.0.1/api/login',
                         data=f'{{"user_name":"{DEFAULT_USER["user_name"]}",'
                              f'"password":"{DEFAULT_USER["password"]}","remember_me":false}}', verify=False)


def test_rate_limiting():
    for i in range(10):
        resp = do_login()
        assert resp.status_code == 200
        session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
        resp.close()
        resp = requests.get('https://127.0.0.1/api/logout', headers={'Cookie': 'session=' + session}, verify=False)
        assert resp.status_code == 200
        resp.close()

    # Set rate limiting to 5 per 3 minutes
    resp = do_login()
    assert resp.status_code == 200
    session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
    resp.close()
    resp = requests.get('https://127.0.0.1/api/csrf', headers={'Cookie': 'session=' + session}, verify=False)
    assert resp.status_code == 200
    csrf_token = resp.content
    resp.close()
    resp = requests.post('https://127.0.0.1/api/settings/plugins/core/CoreService', data=json.dumps(NEW_SETTINGS),
                         headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token,
                                  'content-type': 'application/json;charset=UTF-8'}, verify=False)
    assert resp.status_code == 200
    resp.close()
    time.sleep(10)  # allow settings to apply

    for i in range(5):
        resp = do_login()
        assert resp.status_code == 200
        session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
        resp.close()
        resp = requests.get('https://127.0.0.1/api/logout', headers={'Cookie': 'session=' + session}, verify=False)
        assert resp.status_code == 200
        resp.close()

    resp = do_login()
    assert resp.status_code == 429
    resp.close()

    time.sleep(60 * 3 + 5)

    # Cleanup
    resp = do_login()
    assert resp.status_code == 200
    session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
    resp.close()
    resp = requests.get('https://127.0.0.1/api/csrf', headers={'Cookie': 'session=' + session}, verify=False)
    assert resp.status_code == 200
    csrf_token = resp.content
    resp.close()

    resp = requests.post('https://127.0.0.1/api/settings/plugins/core/CoreService', data=json.dumps(OLD_SETTINGS),
                         headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token,
                                  'content-type': 'application/json;charset=UTF-8'}, verify=False)
    assert resp.status_code == 200
    resp.close()
