export const actionsMeta = {
  aws_ec2_add_tags: {
    title: 'Add Tag to Amazon EC2 Instance',
  },
  aws_ec2_delete_tags: {
    title: 'Remove Tag from Amazon EC2 Instance',
  },
  aws_ec2_start_instance: {
    title: 'Start Amazon EC2 Instance',
  },
  aws_ec2_stop_instance: {
    title: 'Stop Amazon EC2 Instance',
  },
  azure_add_tags: {
    title: 'Add Tag to Microsoft Azure Cloud Instance',
  },
  run_executable_windows: {
    title: 'Deploy on Windows Device',
  },
  qualys_add_tag: {
    title: 'Add Tag to Host Asset in Qualys Cloud Platform',
  },
  qualys_remove_tag: {
    title: 'Remove Tag From Host Asset in Qualys Cloud Platform',
  },
  refetch_action: {
    title: 'Refetch Asset Entity',
  },
  run_executable_linux: {
    title: 'Deploy on Linux Device',
  },
  run_command_windows: {
    title: 'Deploy Files and Run Windows Shell Command',
  },
  run_command_linux: {
    title: 'Deploy Files and Run Linux Shell Command',
  },
  run_wmi_scan: {
    title: 'Run WMI Scan',
  },
  run_linux_ssh_scan: {
    title: 'Run Linux SSH Scan',
  },
  shodan_enrichment: {
    title: 'Enrich Device Data with Shodan',
  },
  portnox_enrichment: {
    title: 'Enrich Device Data with Portnox',
  },
  censys_enrichment: {
    title: 'Enrich Device Data with Censys',
  },
  create_cherwell_incident: {
    title: 'Create Cherwell Incident',
  },
  haveibeenpwned_enrichment: {
    title: 'Enrich User Data with Have I Been Pwned',
  },
  webscan_enrichment: {
    title: 'Enrich Device Data with Web Server Information',
  },
  carbonblack_isolate: {
    title: 'Isolate in VMware Carbon Black EDR',
  },
  carbonblack_unisolate: {
    title: 'Unisolate in VMware Carbon Black EDR',
  },
  cybereason_isolate: {
    title: 'Isolate in Cybereason Deep Detect & Respond',
  },
  cybereason_unisolate: {
    title: 'Unisolate in Cybereason Deep Detect & Respond',
  },
  limacharlie_isolate: {
    title: 'Isolate in LimaCharlie',
  },
  limacharlie_unisolate: {
    title: 'Unisolate in LimaCharlie',
  },
  cybereason_tag: {
    title: 'Tag in Cybereason Deep Detect & Respond',
  },
  sentinelone_initiate_scan_action: {
    title: 'Initiate SentinelOne Scan',
  },
  qualys_create_asset: {
    title: 'Add IPs to Qualys Cloud Platform',
  },
  tenable_io_add_ips_to_target_group: {
    title: 'Add IPs to Tenable.io Target Group',
  },
  desktop_central_do_som_action: {
    title: 'Manage Computer in ManageEngine Desktop Central SoM'
  },
  rapid7_ips_to_site: {
        title: 'Add IPs to Rapid7 InsightVM Site'
    },tenable_io_create_asset: {
    title: 'Create Tenable.io Asset',
  },
  tenable_io_ips_scans: {
    title: 'Add IPs to Tenable.io Scan',
  },
  tenable_io_tag_assets: {
    title: 'Tag Tenable.io Assets'
  },
  create_fresh_service_incident: {
    title: 'Create Freshservice Ticket',
  },
  tenable_sc_add_ips_to_asset: {
    title: 'Add IPs to Tenable.sc Asset',
  },
  patch_device_windows: {
    title: 'Patch Windows Device',
  },
  patch_device_linux: {
    title: 'Patch Linux Device',
  },
  block_fw_paloalto: {
    title: 'Block Device in Palo Alto Networks Panorama',
  },
  create_service_now_computer: {
    title: 'Create ServiceNow Computer',
  },
  update_cherwell_computer: {
    title: 'Update Cherwell Computer',
  },
  create_ivanti_sm_computer: {
    title: 'Create Ivanti Service Manager Computer',
  },
  update_ivanti_sm_computer: {
    title: 'Update Ivanti Service Manager Computer',
  },
  create_cherwell_computer: {
    title: 'Create Cherwell Computer',
  },
  update_service_now_computer: {
    title: 'Update ServiceNow Computer',
  },
  carbonblack_defense_change_policy: {
    title: 'Change VMware Carbon Black Cloud Policy',
  },
  carbonblack_defense_quarantine: {
    title: 'Isolate VMware Carbon Black Cloud Device',
  },
  carbonblack_defense_unquarantine: {
    title: 'Unisolate VMware Carbon Black Cloud Device',
  },
  enable_entities: {
    title: 'Enable Users or Devices',
  },
  slack_send_message: {
    title: 'Send Slack Message',
  },
  change_ldap_attribute: {
    title: 'Update LDAP Attributes of Users or Devices',
  },
  disable_entities: {
    title: 'Disable Users or Devices',
  },
  create_service_now_incident: {
    title: 'Create ServiceNow Incident',
  },
  create_service_now_incident_per_entity: {
    title: 'Create ServiceNow Incident per Entity',
  },
  create_jira_incident: {
    title: 'Create Jira Issue',
  },
  jira_incident_per_entity_action: {
    title: 'Create Jira Issue per Entity',
  },
  jira_create_asset: {
    title: 'Add Asset to Jira Assets Platform',
  },
  create_sysaid_incident: {
    title: 'Create SysAid Incident',
  },
  create_zendesk_ticket: {
    title: 'Create Zendesk Ticket',
  },
  opsgenie_create_alert: {
    title: 'Create Atlassian Opsgenie Alert',
  },
  create_remedy_ticket: {
    title: 'Create BMC Helix Remedy Ticket',
  },
  send_emails: {
    title: 'Send Email',
  },
  send_csv_to_share: {
    title: 'Send CSV to Share',
  },
  send_csv_to_scp: {
    title: 'Send CSV to SCP',
  },
  send_csv_to_s3: {
    title: 'Send CSV to Amazon S3',
  },
  send_json_to_s3: {
    title: 'Send JSON to Amazon S3'
  },
  automox_install_update: {
    title: 'Automox Install Update',
  },
  send_email_to_entities: {
    title: 'Send Email to Entities',
  },
  notify_syslog: {
    title: 'Send to Syslog System',
  },
  send_https_log: {
    title: 'Send to HTTPS Log System',
  },
  send_to_webhook: {
    title: 'Send to Webhook',
  },
  create_notification: {
    title: 'Push System Notification',
  },
  tag: {
    title: 'Add Tag',
  },
  untag: {
    title: 'Remove Tag',
  },
  add_custom_data: {
    title: 'Add Custom Data',
  },
  remove_subdomain_from_dns_made_easy: {
    title: 'Remove Subdomain from DNS Made Easy',
  },
  aws_operations: {
    title: 'Manage AWS Services',
    items: ['aws_ec2_start_instance', 'aws_ec2_stop_instance', 'aws_ec2_add_tags', 'aws_ec2_delete_tags'],
  },
  azure_operations: {
    title: 'Manage Microsoft Azure Services',
    items: ['azure_add_tags'],
  },
  run_command: {
    title: 'Deploy Files and Run Commands',
    items: ['run_command_windows', 'run_command_linux', 'run_wmi_scan', 'run_linux_ssh_scan'],
  },
  isolate_edr: {
    title: 'Execute Endpoint Security Agent Action',
    items: ['carbonblack_isolate', 'carbonblack_unisolate', 'cybereason_isolate', 'cybereason_unisolate', 'cybereason_tag', 'carbonblack_defense_change_policy', 'carbonblack_defense_quarantine', 'carbonblack_defense_unquarantine', 'sentinelone_initiate_scan_action', 'automox_install_update', 'desktop_central_do_som_action', 'limacharlie_isolate', 'limacharlie_unisolate'],
  },
  scan_va: {
    title: 'Update VA Coverage',
    items: ['qualys_create_asset', 'qualys_add_tag', 'qualys_remove_tag', 'tenable_sc_add_ips_to_asset', 'tenable_io_add_ips_to_target_group', 'tenable_io_create_asset', 'tenable_io_ips_scans', 'tenable_io_tag_assets', 'rapid7_ips_to_site'],
  },
  patch_device: {
    title: 'Patch Device',
    items: ['patch_device_windows', 'patch_device_linux'],
  },
  block_fw: {
    title: 'Block Device in Firewall',
    items: ['block_fw_paloalto'],
  },
  create_cmdb_computer: {
    title: 'Manage CMDB Computer',
    items: ['create_service_now_computer', 'update_service_now_computer', 'create_cherwell_computer', 'update_cherwell_computer', 'jira_create_asset', 'create_ivanti_sm_computer', 'update_ivanti_sm_computer'],
  },
  manage_directory: {
    title: 'Manage Microsoft Active Directory (AD) Services',
    items: ['enable_entities', 'disable_entities', 'change_ldap_attribute'],
  },
  create_incident: {
    title: 'Create Incident',
    items: ['create_service_now_incident', 'create_service_now_incident_per_entity', 'create_jira_incident', 'jira_incident_per_entity_action', 'create_sysaid_incident', 'create_zendesk_ticket', 'create_remedy_ticket', 'create_fresh_service_incident', 'opsgenie_create_alert', 'create_cherwell_incident'],
  },
  enrich_device_or_user_data: {
    title: 'Enrich Device or User Data',
    items: ['shodan_enrichment', 'censys_enrichment', 'haveibeenpwned_enrichment', 'portnox_enrichment', 'webscan_enrichment'],
  },
  notify: {
    title: 'Notify',
    items: ['send_emails', 'send_email_to_entities', 'notify_syslog', 'send_https_log', 'send_to_webhook', 'create_notification', 'slack_send_message', 'send_csv_to_share', 'send_csv_to_s3', 'send_json_to_s3', 'send_csv_to_scp'],
  },
  axonius: {
    title: 'Axonius Utilities',
    items: ['tag', 'untag', 'add_custom_data', 'refetch_action'],
  },
  manage_dns_services: {
    title: 'Manage DNS Services',
    items: ['remove_subdomain_from_dns_made_easy']
  },
};

export const mainCondition = 'main';

export const successiveActionsList = ['success', 'failure', 'post'];

export const enforcementConditions = {
  main: {
    icon: '', iconClass: '',
  },
  success: {
    icon: 'check-circle', iconClass: 'icon-success',
  },
  failure: {
    icon: 'close-circle', iconClass: 'icon-error',
  },
  post: {
    icon: 'info-circle', iconClass: 'icon-info',
  },
};

export const createdToastMessages = {
  main: 'Enforcement set and main action created successfully',
  trigger: 'Trigger created successfully',
  success: 'Success action created successfully',
  post: 'Post action created successfully',
  failure: 'Failure action created successfully',
};

export const updatedToastMessages = {
  main: 'Main action updated successfully',
  trigger: 'Trigger updated successfully',
  success: 'Success action updated successfully',
  post: 'Post action updated successfully',
  failure: 'Failure action updated successfully',
};

export const deletedToastMessages = {
  trigger: 'Trigger deleted successfully',
  success: 'Success action deleted successfully',
  post: 'Post action deleted successfully',
  failure: 'Failure action deleted successfully',
};

export const actionCategories = [
  'notify', 'create_incident', 'axonius',
  'enrich_device_or_user_data', 'create_cmdb_computer', 'scan_va', 'run_command', 'isolate_edr',
  'manage_directory', 'aws_operations', 'azure_operations', 'manage_dns_services',
];
