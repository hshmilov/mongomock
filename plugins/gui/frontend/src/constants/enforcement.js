export const actionsMeta = {
    run_executable_windows: {
        title: 'Deploy on Windows Device'
    },
    run_executable_linux: {
        title: 'Deploy on Linux Device'
    },
    run_command_windows: {
        title: 'Run Windows Shell Command'
    },
    run_command_linux: {
        title: 'Run Linux Shell Command'
    },
    run_wmi_scan: {
        title: 'Run WMI Scan'
    },
    run_linux_ssh_scan : {
        title: 'Run Linux SSH Scan'
    },
    shodan_enrichment: {
        title: 'Enrich Device Data with Shodan'
    },
    portnox_enrichment: {
        title: 'Enrich Device Data with Portnox'
    },
    censys_enrichment: {
        title: 'Enrich Device Data with Censys'
    },
    haveibeenpwned_enrichment: {
        title: 'Enrich User Data with Have I Been Pwned'
    },
    webscan_enrichment: {
        title: 'Enrich Device Data with Web Server Information'
    },
    carbonblack_isolate: {
        title: 'Isolate in Carbon Black CB Response'
    },
    carbonblack_unisolate: {
        title: 'Unisolate in Carbon Black CB Response'
    },
    cybereason_isolate: {
        title: 'Isolate in Cybereason Deep Detect & Respond'
    },
    cybereason_unisolate: {
        title: 'Unisolate in Cybereason Deep Detect & Respond'
    },
    sentinelone_initiate_scan_action: {
        title: 'Initiate SentinelOne Scan'
    },
    scan_with_qualys: {
        title: 'Add to Qualys Cloud Platform'
    },
    tenable_io_add_ips_to_target_group: {
        title: 'Add IPs to Tenable.io Target Group'
    },
    tenable_io_create_asset: {
        title: 'Create Tenable.io Asset'
    },
    create_fresh_service_incident: {
        title: 'Create Freshservice Ticket'
    },
    tenable_sc_add_ips_to_asset: {
        title: 'Add IPs to Tenable.sc Asset'
    },
    patch_device_windows: {
        title: 'Patch Windows Device'
    },
    patch_device_linux: {
        title: 'Patch Linux Device'
    },
    block_fw_paloalto: {
        title: 'Block Device in Palo Alto Networks Panorama'
    },
    create_service_now_computer: {
        title: 'Create ServiceNow Computer'
    },
    carbonblack_defense_change_policy: {
        title: 'Change Carbon Black CB Defense Policy'
    },
    carbonblack_defense_quarantine: {
        title: 'Isolate Carbon Black CB Defense Device'
    },
    carbonblack_defense_unquarantine: {
        title: 'Unisolate Carbon Black CB Defense Device'
    },
    enable_entities: {
        title: 'Enable Users or Devices'
    },
    slack_send_message: {
        title: 'Send Slack Message'
    },
    change_ldap_attribute: {
        title: 'Update LDAP Attributes of Users or Devices'
    },
    disable_entities: {
        title: 'Disable Users or Devices'
    },
    create_service_now_incident: {
        title: 'Create ServiceNow Incident'
    },
    create_service_now_incident_per_entity: {
        title: 'Create ServiceNow Incident per Entity'
    },
    create_jira_incident: {
        title: 'Create Jira Issue'
    },
    jira_incident_per_entity_action: {
        title: 'Create Jira Issue Per Entity'
    },
    create_sysaid_incident: {
        title: 'Create SysAid Incident'
    },
    create_zendesk_ticket: {
        title: 'Create Zendesk Ticket'
    },
    create_remedy_ticket: {
        title: 'Create BMC Helix Remedy Ticket'
    },
    send_emails: {
        title: 'Send Email'
    },
    send_csv_to_share: {
        title: 'Send CSV to Share'
    },
    send_csv_to_s3: {
        title: 'Send CSV to Amazon S3'
    },
    automox_install_update: {
        title: 'Automox Install Update'
    },
    send_email_to_entities: {
        title: 'Send Email to Entities'
    },
    notify_syslog: {
        title: 'Send to Syslog System'
    },
    send_https_log: {
        title: 'Send to HTTPS Log System'
    },
    send_to_webhook: {
        title: 'Send to Webhook'
    },
    create_notification: {
        title: 'Push System Notification'
    },
    tag: {
        title: 'Add Tag'
    },
    untag: {
        title: 'Remove Tag'
    },
    add_custom_data: {
        title: 'Add Custom Data'
    },
    deploy_software: {
        title: 'Deploy Software',
        items: ['run_executable_windows']
    },
    run_command: {
        title: 'Run Command',
        items: ['run_command_windows', 'run_command_linux', 'run_wmi_scan', 'run_linux_ssh_scan']
    },
    isolate_edr: {
        title: 'Execute Endpoint Security Agent Action',
        items: ['carbonblack_isolate', 'carbonblack_unisolate', 'cybereason_isolate', 'cybereason_unisolate', 'carbonblack_defense_change_policy', 'carbonblack_defense_quarantine', 'carbonblack_defense_unquarantine', 'sentinelone_initiate_scan_action', 'automox_install_update']
    },
    scan_va: {
        title: 'Add Device to VA Scan',
        items: ['tenable_sc_add_ips_to_asset', 'tenable_io_add_ips_to_target_group', 'tenable_io_create_asset', 'scan_with_qualys']
    },
    patch_device: {
        title: 'Patch Device',
        items: ['patch_device_windows', 'patch_device_linux']
    },
    block_fw: {
        title: 'Block Device in Firewall',
        items: ['block_fw_paloalto']
    },
    create_cmdb_computer: {
        title: 'Create CMDB Computer',
        items: ['create_service_now_computer']
    },
    manage_directory: {
        title: 'Manage Microsoft Active Directory (AD) Services',
        items: ['enable_entities', 'disable_entities', 'change_ldap_attribute']
    },
    create_incident: {
        title: 'Create Incident',
        items: ['create_service_now_incident', 'create_service_now_incident_per_entity', 'create_jira_incident', 'jira_incident_per_entity_action', 'create_sysaid_incident', 'create_zendesk_ticket', 'create_remedy_ticket', 'create_fresh_service_incident']
    },
    enrich_device_or_user_data: {
        title: 'Enrich Device or User Data',
        items: ['shodan_enrichment', 'censys_enrichment', 'haveibeenpwned_enrichment', 'portnox_enrichment','webscan_enrichment']
    },
    notify: {
        title: 'Notify',
        items: ['send_emails', 'send_email_to_entities', 'notify_syslog', 'send_https_log', 'send_to_webhook', 'create_notification', 'slack_send_message', 'send_csv_to_share', 'send_csv_to_s3']
    },
    axonius: {
        title: 'Axonius Utilities',
        items: ['tag', 'untag', 'add_custom_data']
    }
}


export const mainCondition = 'main'

export const successCondition = 'success'
export const failCondition = 'failure'
export const postCondition = 'post'

export const actionCategories = [
    'notify', 'create_incident', 'axonius',
    'enrich_device_or_user_data', 'scan_va', 'run_command', 'isolate_edr',
    'create_cmdb_computer', 'manage_directory',
    'deploy_software'
]