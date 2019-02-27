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
    carbonblack_isolate: {
        title: 'Isolate in CarbonBlack'
    },
    carbonblack_unisolate: {
        title: 'Unisolate in CarbonBlack'
    },
    cybereason_isolate: {
        title: 'Isolate in Cybereason'
    },
    cybereason_unisolate: {
        title: 'Unisolate in Cybereason'
    },
    scan_with_qualys: {
        title: 'Add to Qualys'
    },
    scan_with_tenable: {
        title: 'Add to Tenable'
    },
    patch_device_windows: {
        title: 'Patch Windows Device'
    },
    patch_device_linux: {
        title: 'Patch Linux Device'
    },
    block_fw_paloalto: {
        title: 'Block in Palo Alto'
    },
    create_service_now_computer: {
        title: 'Create ServiceNow Computer'
    },
    enable_entities: {
        title: 'Enable users or devices'
    },
    disable_entities: {
        title: 'Disable users or devices'
    },
    create_service_now_incident: {
        title: 'Create ServiceNow Incident'
    },
    create_jira_incident: {
        title: 'Create Jira Issue'
    },
    create_sysaid_incident: {
        title: 'Create Sysaid Incident'
    },
    send_emails: {
        title: 'Send Mail'
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
        items: ['run_command_windows', 'run_command_linux']
    },
    isolate_edr: {
        title: 'Isolate Device in EDR',
        items: ['carbonblack_isolate', 'carbonblack_unisolate', 'cybereason_isolate', 'cybereason_unisolate']
    },
    scan_va: {
        title: 'Add Device to VA Scan',
        items: ['scan_with_qualys', 'scan_with_tenable']
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
        title: 'Manage Active Directory Services',
        items: ['enable_entities', 'disable_entities']
    },
    create_incident: {
        title: 'Create Incident',
        items: ['create_service_now_incident', 'create_jira_incident', 'create_sysaid_incident']
    },
    notify: {
        title: 'Notify',
        items: ['send_emails', 'notify_syslog', 'send_https_log', 'create_notification']
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
    'deploy_software', 'run_command', 'isolate_edr', 'scan_va',
    'patch_device', 'block_fw', 'create_cmdb_computer', 'manage_directory',
    'notify', 'create_incident', 'axonius'
]