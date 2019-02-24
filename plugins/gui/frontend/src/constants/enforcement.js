export const actionsMeta = {
    run_executable_windows: {
        title: 'Deploy on Windows Device'
    },
    enable_entities: {
        title: 'Enable users or devices'
    },
    disable_entities: {
        title: 'Disable users or devices'
    },
    run_executable_linux: {
        title: 'Deploy on Linux Device'
    },
    run_command_windows: {
        title: 'Run Windows CMD'
    },
    run_command_linux: {
        title: 'Run Shell Script'
    },
    carbonblack_isolate: {
        title: 'Isolate in CarbonBlack'
    },
    carbonblack_unisolate: {
        title: 'Remove isolation in CarbonBlack'
    },
    scan_with_tenable: {
        title: 'Scan in Tenable'
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
    create_service_now_incident: {
        title: 'Create ServiceNow Incident'
    },
    create_jira_incident: {
        title: 'Create Jira Issue'
    },
    send_emails: {
        title: 'Send Mail'
    },
    notify_syslog: {
        title: 'Send to Syslog System'
    },
    send_https_log: {
        title: 'Send to Https Log System'
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
        items: ['run_executable_windows', 'run_executable_linux', 'enable_entities', 'disable_entities']
    },
    run_command: {
        title: 'Run Command',
        items: ['run_command_windows', 'run_command_linux']
    },
    isolate_edr: {
        title: 'Isolate Device in EDR',
        items: ['carbonblack_isolate', 'carbonblack_unisolate']
    },
    scan_va: {
        title: 'Scan Device in VA',
        items: ['scan_with_tenable']
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
    create_incident: {
        title: 'Create Incident',
        items: ['create_service_now_incident', 'create_jira_incident']
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
    'patch_device', 'block_fw', 'create_cmdb_computer', 'notify', 'create_incident',
    'axonius'
]