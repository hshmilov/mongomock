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
        title: 'Enrich Device Data from Shodan'
    },
    haveibeenpwned_enrichment: {
        title: 'Enrich User Data from Have I Been Pwned'
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
    enable_entities: {
        title: 'Enable Users or Devices'
    },
    slack_send_message: {
        title: 'Send Slack Message'
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
    create_sysaid_incident: {
        title: 'Create SysAid Incident'
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
    send_email_to_entities: {
        title: 'Send Email to Entities'
    },
    notify_syslog: {
        title: 'Send to Syslog System'
    },
    send_https_log: {
        title: 'Send to HTTPS Log System'
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
        items: ['run_executable_windows', 'run_executable_linux']
    },
    run_command: {
        title: 'Run Command',
        items: ['run_command_windows', 'run_command_linux', 'run_wmi_scan', 'run_linux_ssh_scan']
    },
    isolate_edr: {
        title: 'Execute Endpoint Security Agent Action',
        items: ['carbonblack_isolate', 'carbonblack_unisolate', 'cybereason_isolate', 'cybereason_unisolate', 'carbonblack_defense_change_policy', 'sentinelone_initiate_scan_action']
    },
    scan_va: {
        title: 'Add Device to VA Scan',
        items: ['tenable_sc_add_ips_to_asset', 'tenable_io_add_ips_to_target_group', 'scan_with_qualys']
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
        items: ['enable_entities', 'disable_entities']
    },
    create_incident: {
        title: 'Create Incident',
        items: ['create_service_now_incident', 'create_service_now_incident_per_entity', 'create_jira_incident', 'create_sysaid_incident']
    },
    enrich_device_data: {
        title: 'Enrich Device and User Data',
        items: ['shodan_enrichment', 'haveibeenpwned_enrichment'],
    },
    notify: {
        title: 'Notify',
        items: ['send_emails', 'send_email_to_entities', 'notify_syslog', 'send_https_log', 'create_notification', 'slack_send_message', 'send_csv_to_share', 'send_csv_to_s3']
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
    'deploy_software', 'run_command', 'isolate_edr', 'scan_va','enrich_device_data',
    'block_fw', 'create_cmdb_computer', 'manage_directory',
    'notify', 'create_incident', 'axonius'
]
