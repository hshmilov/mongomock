

export const UPDATE_EMPTY_STATE = 'UPDATE_EMPTY_STATE'

export const START_TOUR = 'START_TOUR'
export const CHANGE_TOUR_STATE = 'CHANGE_TOUR_STATE'
export const UPDATE_TOUR_STATE = 'UPDATE_TOUR_STATE'
export const NEXT_TOUR_STATE = 'NEXT_TOUR_STATE'
export const STOP_TOUR = 'STOP_TOUR'

export const onboarding = {
	/*
	This module is responsible for walking users through the capabilities of the system.
	It divides into two cases:
		1. Empty states - when users 'land' on a feature they never used before or try to do something that depends on
		   another operation they never performed.
		2. Tour states - sequential states that prompt users to perform steps, that will make them complete use cases
		   of the system, so they learn how it is done. Tour is suggested on the first use and always accessible.
	 */
	state: {
		emptyStates: {
			mailSettings: false,
			syslogSettings: false,
		},
		tourStates: {
			active: false,
			current: '',
			defs: {
				'adapters': {
					id: 'adapters', title: 'CONNECT YOUR NETWORK', align: 'right', fixed: true,
					content: 'Axonius uses Adapters to collect and correlate device and user information from your systems.'
				},
				'activeDirectory': {
					id: 'active_directory_adapter', title: 'Active Directory ADAPTER', queue: 'adapters', align: 'right',
					content: 'If you use ActiveDirectory, click to configure it.',
					actions: [
						{ title: 'SKIP', state: 'network' }
					]
				},
				'addServer': {
					id: 'new_server', title: 'CONFIGURE YOUR SERVER', align: 'left',
					content: 'This adapter can connect to any server you have credentials for.\nClick to fill them in.'
				},
				'saveServer': {
					id: 'save_server', title: 'SAVE CREDENTIALS', align: 'right', fixed: true,
					content: 'Fill in all required fields, then click to connect the server.',
				},
				'successServer': {
					id: 'status_server', title: 'SERVER CONNECTED', align: 'bottom', emphasize: false,
					content: 'The green checkmark icon indicates that the server was added and Axonius was able connect to it.',
					actions: [
						{ title: 'Next', state: 'backAdapters' }
					]
				},
				'errorServer': {
					id: 'status_server', title: 'PROBLEM WITH CREDENTIALS', align: 'bottom',
					content: 'The red exclamation icon indicates that a connection to the server could not be established.\nClick to view the error and try again.',
				},
				'backAdapters': {
					id: 'adapters', title: 'CONNECT YOUR NETWORK', align: 'right', fixed: true,
					content: 'Click to review your Adapters.'
				},
				'network': {
					title: 'NETWORK ADAPTERS', align: 'center', queue: 'adapters',
					content: 'Which of the following switches/routers do you use most?',
					actions: [
						{ title: 'Cisco', state: 'cisco' },
						{ title: 'Juniper', state: 'juniper' },
						{ title: 'Fortinet', state: 'fortinet' },
						{ title: 'Infoblox', state: 'infoblox' },
						{ title: 'SKIP', state: 'virtualizationCloud' }
					]
				},
				'cisco': {
					title: 'Cisco ADAPTERS', align: 'center',
					content: 'Which Cisco management solution do you use?',
					actions: [
						{ title: 'Cisco Prime', state: 'ciscoPrime' },
						{ title: 'Cisco Meraki', state: 'ciscoMeraki' },
						{ title: 'Cisco Switch/Router (direct connection, no management solution)', state: 'ciscoRegular' },
						{ title: 'SKIP', state: 'networkNoCisco'}
					]
				},
				'ciscoPrime': {
					id: 'cisco_prime_adapter', title: 'Cisco Prime ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'ciscoMeraki': {
					id: 'cisco_meraki_adapter', title: 'Cisco Meraki ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'ciscoRegular': {
					id: 'cisco_adapter', title: 'Cisco ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'networkNoCisco': {
					title: 'NETWORK ADAPTERS', align: 'center',
					content: 'Which other major switch/router do you use?',
					actions: [
						{ title: 'Juniper', state: 'juniper' },
						{ title: 'Fortinet', state: 'fortinet' },
						{ title: 'Infoblox', state: 'infoblox' },
						{ title: 'SKIP', state: 'virtualizationCloud' }
					]
				},
				'juniper': {
					title: 'Juniper ADAPTERS', align: 'center',
					content: 'Which Juniper management solution do you use?',
					actions: [
						{ title: 'Juniper Junos', state: 'juniperJunos' },
						{ title: 'Juniper Junos Space', state: 'juniperJunosSpace' },
						{ title: 'SKIP', state: 'networkNoJuniper' }
					]
				},
				'juniperJunos': {
					id: 'junos_adapter', title: 'Juniper Junos ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'juniperJunosSpace': {
					id: 'juniper_adapter', title: 'Juniper Junos Space ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'networkNoJuniper': {
					title: 'NETWORK ADAPTERS', align: 'center', queue: 'adapters',
					content: 'Which other major switch/router do you use?',
					actions: [
						{ title: 'Cisco', state: 'cisco' },
						{ title: 'Fortinet', state: 'fortinet' },
						{ title: 'Infoblox', state: 'infoblox' },
						{ title: 'SKIP', state: 'virtualizationCloud' }
					]
				},
				'fortinet': {
					id: 'fortigate_adapter', title: 'Fortinet Fortigate ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'infoblox': {
					id: 'infoblox_adapter', title: 'Infoblox ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'virtualizationCloud': {
					title: 'CLOUD PROVIDERS', align: 'center', queue: 'adapters',
					content: 'Which of the following cloud providers do you use most?',
					actions: [
						{ title: 'Amazon Elastic', state: 'aws' },
						{ title: 'Microsoft Azure', state: 'azure' },
						{ title: 'Google Compute/Kubernetes Engine', state: 'gce' },
						{ title: 'IBM Cloud', state: 'ibmCloud' },
						{ title: 'SKIP', state: 'virtualizationLocal' }
					]
				},
				'gce': {
					id: 'gce_adapter', title: 'Google Compute/Kubernetes Engine', align: 'right',
					content: 'Click to configure it.'
				},
				'aws': {
					id: 'aws_adapter', title: 'Amazon Elastic ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'azure': {
					id: 'azure_adapter', title: 'Microsoft Azure ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'ibmCloud': {
					id: 'softlayer_adapter', title: 'IBM Cloud ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'virtualizationLocal': {
					title: 'VIRTUALIZATION SOLUTIONS', align: 'center', queue: 'adapters',
					content: 'Which virtualization solution do you use most?',
					actions: [
						{ title: 'Microsoft Hyper-V', state: 'hyperV' },
						{ title: 'OpenStack', state: 'openStack' },
						{ title: 'Oracle VM', state: 'oracleVM' },
						{ title: 'VMWare ESXi', state: 'esx' },
						{ title: 'SKIP', state: 'agent' }
					]
				},
				'esx': {
					id: 'esx_adapter', title: 'VMWare ESXi ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'hyperV': {
					id: 'hyper_v_adapter', title: 'Microsoft Hyper-V ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'openStack': {
					id: 'openstack_adapter', title: 'OpenStack ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'oracleVM': {
					id: 'oracle_vm_adapter', title: 'Oracle VM ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'agent': {
					title: 'ENDPOINT PROTECTION AGENT', align: 'center', queue: 'adapters',
					content: 'Which is the most common Endpoint Protection or EDR Agent you use?',
					actions: [
						{ title: 'Carbon Black', state: 'carbonBlack' },
						{ title: 'enSilo', state: 'enSilo' },
						{ title: 'McAfee ePO', state: 'epo' },
						{ title: 'Minerva Labs', state: 'minerva'},
						{ title: 'Secdo', state: 'secdo' },
						{ title: 'SentinelOne', state: 'sentinelOne' },
						{ title: 'Symantec', state: 'symantec' },
						{ title: 'FireEye HX', state: 'fireeyeHX' },
						{ title: 'CrowdStrike Falcon', state: 'crowdStrike' },
						{ title: 'FireEye HX', state: 'fireeyeHX' },
						{ title: 'Sophos', state: 'sophos' },
						{ title: 'Cylance', state: 'cylance' },
						{ title: 'SKIP', state: 'agentIT' }
					]
				},
				'cylance': {
					id: 'cylance_adapter', title: 'CylancePROTECT', align: 'right',
					content: 'Click to configure it.'
				},
				'sophos': {
					id: 'sophos_adapter', title: 'Sophos Endpoint Protection', align: 'right',
					content: 'Click to configure it.'
				},
				'crowdStrike': {
					id: 'crowd_strike_adapter', title: 'CrowdStrike Falcon', align: 'right',
					content: 'Click to configure it.'
				},
				'epo': {
					id: 'epo_adapter', title: 'McAfee ePO', align: 'right',
					content: 'Click to configure it.'
				},
				'symantec': {
					id: 'symantec_adapter', title: 'Symantec ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'carbonBlack': {
					title: 'Carbon Black', align: 'center',
					content: 'Which Carbon Black product do you use?',
					actions: [
						{ title: 'Cb Response', state: 'carbonBlackResponse' },
						{ title: 'Cb Protection', state: 'carbonBlackProtection' },
						{ title: 'Cb Defense', state: 'carbonBlackDefense' }
					]
				},
				'carbonBlackResponse': {
					id: 'carbonblack_response_adapter', title: 'CarbonBlack Response ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'carbonBlackProtection': {
					id: 'carbonblack_protection_adapter', title: 'CarbonBlack Protection ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'carbonBlackDefense': {
					id: 'carbonblack_defense_adapter', title: 'CarbonBlack Defense ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'minerva': {
					id: 'minerva_adapter', title: 'Minerva Labs ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'enSilo': {
					id: 'ensilo_adapter', title: 'enSilo Endpoint Protection', align: 'right',
					content: 'Click to configure it.'
				},
				'secdo': {
					id: 'secdo_adapter', title: 'Secdo Endpoint Protection', align: 'right',
					content: 'Click to configure it.'
				},
				'sentinelOne': {
					id: 'sentinelone_adapter', title: 'SentinelOne', align: 'right',
					content: 'Click to configure it.'
				},
				'fireeyeHX': {
					id: 'fireeye_hx_adapter', title: 'FireEye HX ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'agentIT': {
					title: 'IT AGENT', align: 'center', queue: 'adapters',
					content: 'Which IT agent do you use?',
					actions: [
						{ title: 'Bomgar', state: 'bomgar'},
						{ title: 'Chef', state: 'chef'},
						{ title: 'IBM BigFix', state: 'bigFix'},
						{ title: 'Kaseya', state: 'kaseya'},
						{ title: 'ManageEngine', state: 'manageEngine'},
						{ title: 'Microsoft SCCM', state: 'sccm'},
						{ title: 'ObserveIT', state: 'observeIT'},
						{ title: 'Puppet', state: 'puppet'},
						{ title: 'Symantec Altiris', state: 'symantecAltiris' },
						{ title: 'SKIP', state: 'va'}
					]
				},
				'sccm': {
					id: 'sccm_adapter', title: 'Microsoft SCCM ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'bigFix': {
					id: 'bigfix_adapter', title: 'IBM Bigfix ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'puppet': {
					id: 'puppet_adapter', title: 'Puppet ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'chef': {
					id: 'chef_adapter', title: 'Chef ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'bomgar': {
					id: 'bomgar_adapter', title: 'Bomgar Remote Support ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'manageEngine': {
					id: 'desktop_central_adapter', title: 'ManageEngine Desktop Central ADAPTER', align: 'bottom',
					content: 'Click to configure it.'
				},
				'kaseya': {
					id: 'kaseya_adapter', title: 'Kaseya VSA ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'observeIT': {
					id: 'observeit_csv_adapter', title: 'ObserveIT ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'symantecAltiris': {
					id: 'symantec_altiris_adapter', title: 'Symantec Altiris ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'va':  {
					title: 'VULNERABILITY ASSESSMENT TOOLS', align: 'center', queue: 'adapters',
					content: 'Which Vulnerability Assessment tool do you use?',
					actions: [
						{ title: 'Qualys', state: 'qualys' },
						{ title: 'Rapid 7 Nexpose', state: 'nexpose' },
						{ title: 'Tenable Nessus', state: 'nessus' },
						{ title: 'SKIP', state: 'mdm' }
					]
				},
				'qualys': {
					id: 'qualys_scans_adapter', title: 'Qualys Scanner ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'nexpose': {
					id: 'nexpose_adapter', title: 'Rapid7 Nexpose', align: 'right',
					content: 'Click to configure it.'
				},
				'nessus': {
					id: 'nessus_adapter', title: 'Tenable Nessus ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'mdm': {
					title: 'MDM SOLUTIONS', align: 'center', queue: 'adapters',
					content: 'Which Mobile Device Management solution do you use most?',
					actions: [
						{ title: 'BlackBerry UEM', state: 'blackberry' },
						{ title: 'MobileIron', state: 'mobileIron' },
						{ title: 'VMWare Airwatch', state: 'vmwareAirwatch' },
						{ title: 'G-Suite MDM', state: 'gsuiteMDM' },
						{ title: 'SKIP', state: 'serviceNowAdapter' }
					]
				},
				'mobileIron': {
					id: 'mobileiron_adapter', title: 'MobileIron EMM ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'vmwareAirwatch': {
					id: 'airwatch_adapter', title: 'VMWare Airwatch ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'blackberry': {
					id: 'blackberry_uem_adapter', title: 'Blackberry UEM ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'gsuiteMDM': {
					id: 'mdm_adapter', title: 'G-Suite MDM ADAPTER', align: 'right',
					content: 'Click to configure it.'
				},
				'serviceNowAdapter': {
					id: 'service_now_adapter', title: 'ServiceNow ADAPTER', align: 'right', queue: 'adapters',
					content: 'If you use ServiceNow, click to configure it.',
					actions: [
						{ title: 'SKIP', state: 'oktaAdapter' }
					]
				},
				'oktaAdapter': {
					id: 'okta_adapter', title: 'Okta ADAPTER', align: 'right', queue: 'adapters',
					content: 'If you use Okta, click to configure it.',
					actions: [
						{ title: 'SKIP', state: 'csv' }
					]
				},
				'csv': {
					id: 'csv_adapter', title: 'CSV SERIALS ADAPTER', align: 'right', queue: 'adapters',
					content: 'If you have a CSV file with other devices you want to add, click to configure it.',
					actions: [
						{ title: 'SKIP', state: 'devices' }
					]
				},
				'devices': {
					id: 'devices', title: 'SEE YOUR DEVICES', align: 'right', fixed: true,
					content: 'Click to see all devices that were found and correlated.'
				},
				'bestDevice': {
					title: 'DEVICE VIEW', align: 'bottom', queue: 'devices',
					content: 'Click to view in-depth details about this device.'
				},
				'adaptersData': {
					id: 'specific', title: 'ADAPTERS DATA', align: 'right',
					content: 'Here you can see all device data from its Adapters.'
				},
				'adapterDevice': {
					title: 'DEVICE ADAPTER', emphasize: false,
					content: 'You will see a tab for every Adapter that has device data.',
					actions: [
						{ title: 'Next', state: 'backDevices'}
					]
				},
				'backDevices': {
					id: 'devices', title: 'DEVICES', align: 'right', fixed: true,
					content: 'Click to see your devices.'
				},
				'query': {
					id: 'query_wizard', title: 'QUERY', align: 'left', queue: 'devices',
					content: 'Let\'s query devices by operating system. Click to build the query.'
				},
				'queryField': {
					id: 'query_field', title: 'SELECT FIELD', align: 'top',
					content: 'Click to select the field "OS: Type". You can search for it if it\'s easier.'
				},
				'queryOp': {
					id: 'query_op', title: 'SELECT OPERATOR', align: 'top',
					content: 'Click to select the "equals" operator to compare to a value.'
				},
				'queryValue': {
					id: 'query_value', title: 'SELECT VALUE', align: 'top',
					content: 'Click and select the OS you would like to find.'
				},
				'queryResults': {
					title: 'QUERY RESULTS', align: 'center', queue: 'devices',
					content: 'You\'ll see that the contents of the table changed to show the results of your query.\nYou can always change and refine your query and see new results.',
					actions: [
						{ title: 'Next', state: 'querySave' }
					]
				},
				'querySave': {
					id: 'query_save', title: 'SAVE QUERY', align: 'bottom',
					content: 'Click to name and save your query.'
				},
				'querySaveConfirm': {
					id: 'query_save_confirm', title: 'SAVE QUERY', align: 'right',
					content: 'Fill in the name, then click to save.'
				},
				'queryList': {
					id: 'query_list', title: 'QUERIES LIST', align: 'right',
					content: 'Click to see a list of saved queries and the query history.'
				},
				'querySelect': {
					id: 'query_select', title: 'SELECT A QUERY', align: 'bottom', emphasize: false,
					content: 'Here you see the query you saved as well as predefined queries. Select any query to see the results.'
				},
				'alerts': {
					id: 'alerts', title: 'DEFINE ALERTS', align: 'right', queue: 'devices', fixed: true,
					content: 'Alerts monitor results of queries and take action.'
				},
				'alertNew': {
					id: 'alert_new', title: 'NEW ALERT', align: 'left', queue: 'alerts',
					content: 'Click to create an alert for the query we just saved.'
				},
				'alertName': {
					id: 'alert_name', title: 'ALERT NAME', align: 'right',
					content: 'Give the alert a meaningful name that you\'ll recognize later.'
				},
				'alertQuery': {
					id: 'alert_query', title: 'ALERT QUERY', align: 'right',
					content: 'Select the name of the query you just saved.'
				},
				'alertIncreased': {
					id: 'alert_increased', title: 'ALERT TRIGGER', align: 'right',
					content: 'Select how this alert should be triggered.'
				},
				'alertAbove': {
					id: 'alert_above', title: 'ALERT TRIGGER', align: 'bottom',
					content: 'Choose the number of results that will trigger the alert.'
				},
				'alertAction': {
					id: 'alert_notification', title: 'ALERT ACTION', align: 'right',
					content: 'Choose the action to take when the alert is triggered.'
				},
				'alertSave': {
					id: 'alert_save', title: 'SAVE THE ALERT', align: 'left',
					content: 'Click to save the alert.'
				},
				'settings': {
					id: 'settings', title: 'SETTINGS', align: 'bottom', queue: 'alerts',
					content: 'Choose configuration options for system functionality.'
				},
				'lifecycleRate': {
					id: 'system_research_rate', title: 'DISCOVERY RUN FREQUENCY', align: 'top',
					content: 'Set the number of hours between discovery runs.',
					actions: [
						{ title: 'Next', state: 'lifecycleRun' }
					]
				},
				'lifecycleRun': {
					id: 'run_research', title: 'DISCOVERY RUN NOW', align: 'bottom',
					content: 'Click to start a discovery run now. Once started, you can click to stop at any time.',
					actions: [
						{ title: 'Next', state: 'settingsGlobal' }
					]
				},
				'settingsGlobal': {
					id: 'global-settings-tab', title: 'GLOBAL SYSTEM SETTINGS', align: 'bottom',
					content: 'Configure execution and notification settings here.'
				},
				'global-settings-tab': {
					id: 'syslog_settings', title: 'SYSLOG SERVER CONFIG', align: 'top',
					content: 'Enable and provide syslog credentials here for alerts.',
					actions: [
						{ title: 'Next', state: 'serviceNow' }
					]
				},
				'serviceNow': {
					id: 'service_now_settings', title: 'ServiceNow SERVER CONFIG', align: 'top',
					content: 'Enable and provide ServiceNow credentials here, or use the Adapter (if it is connected) for alerts.',
					actions: [
						{ title: 'Next', state: 'mail' }
					]
				},
				'mail': {
					id: 'email_settings', title: 'MAIL SERVER CONFIG', align: 'top',
					content: 'Enable and provide mail server credentials for alerts.',
					actions: [
						{ title: 'Next', state: 'execution' }
					]
				},
				'execution': {
					id: 'execution_settings', title: 'EXECUTION CONFIG', align: 'top',
					content: 'Enable Axonius to collect information directly from devices in addition to what is collected from Adapters.',
					actions: [
						{ title: 'Next', state: 'maintenance' }
					]
				},
				'maintenance': {
					id: 'maintenance_settings', title: 'MAINTENANCE CONFIG', align: 'top',
					content: 'Enable Axonius to anonymously save analytics info or troubleshoot remotely',
					actions: [
						{ title: 'Next', state: 'settingsGUI' }
					]
				},
				'settingsGUI': {
					id: 'gui-settings-tab', title: 'UI SETTINGS', align: 'bottom',
					content: 'Configure settings related to the system interface.'
				},
				'gui-settings-tab': {
					id: 'system_settings', title: 'DATA TABLES', align: 'top',
					content: 'Configure how frequently devices and users are collected, and determine the default sorting.',
					actions: [
						{ title: 'Next', state: 'okta' }
					]
				},
				'okta': {
					id: 'okta_login_settings', title: 'LOGIN WITH OKTA', align: 'top',
					content: 'If you use Okta, you can log in to Axonius by entering Okta details.',
					actions: [
						{ title: 'Next', state: 'google' }
					]
				},
				'google': {
					id: 'google_login_settings', title: 'LOGIN WITH Google', align: 'top',
					content: 'If you use Google (G-Suite), you can log in to Axonius by entering G-Suite settings.',
					actions: [
						{ title: 'Next', state: 'ldap' }
					]
				},
				'ldap': {
					id: 'ldap_login_settings', title: 'LOGIN WITH LDAP', align: 'top',
					content: 'If you use LDAP, you can log in to Axonius by entering LDAP user details.',
					actions: [
						{ title: 'Next', state: 'saml' }
					]
				},
				'saml': {
					id: 'saml_login_settings', title: 'LOGIN WITH SAML', align: 'top',
					content: 'If you use an identity provider that supports SAML, you can log in to Axonius by entering SAML settings.',
					actions: [
						{ title: 'Next', state: 'dashboard' }
					]
				},
				'dashboard': {
					id: 'dashboard', title: 'DASHBOARD', align: 'right', fixed: true,
					content: 'The Axonius dashboard gives a system-wide snapshot.'
				},
				'dashboardManaged': {
					id: 'managed_coverage', title: 'MANAGEMENT COVERAGE', align: 'right', emphasize: false,
					content: 'The coverage chart shows the percentage of devices managed by an adapter.',
					actions: [
						{ title: 'Next', state: 'dashboardManagedQuery' }
					]
				},
				'dashboardManagedQuery': {
					id: 'managed_coverage', title: 'MANAGEMENT COVERAGE', align: 'bottom',
					content: 'Click to see unmanaged devices.'
				},
				'dashboardBack': {
					id: 'dashboard', title: 'DASHBOARD', align: 'right', fixed: true,
					content: 'Click to return to the dashboard.'
				},
				'dashboardWizard': {
					id: 'dashboard_wizard', title: 'CREATE YOUR OWN CHART', align: 'right',
					content: 'Click to launch the new chart wizard.'
				},
				'wizardIntersect': {
					id: 'metric', title: 'CHART METRIC', align: 'top', fixed: true,
					content: 'Click to choose a metric to base the chart on. Select \'Query Intersection\' for a pie chart showing the intersection between 2-3 queries.'
				},
				'wizardModule': {
					id: 'module', title: 'CHART MODULE', align: 'right', fixed: true,
					content: 'Click to select which data to show. For example, select \'Devices\'.'
				},
				'wizardMain': {
					id: 'baseQuery', title: 'CHART TOTAL', align: 'right', fixed: true,
					content: 'Click to select which query to use for the total. You can leave this empty.',
					actions: [
						{ title: 'Next', state: 'wizardFirst' }
					]
				},
				'wizardFirst': {
					id: 'intersectingFirst', title: 'CHART FIRST SUBSET', align: 'right', fixed: true,
					content: 'Click to select a query for one subset of the graph. For example, select a query you saved.'
				},
				'wizardSecond': {
					id: 'intersectingSecond', title: 'CHART SECOND SUBSET', align: 'right', fixed: true,
					content: 'Click to select a query for another subset of the graph. For example, select the \'DEMO\' query.'
				},
				'wizardName': {
					id: 'chart_name', title: 'CHART NAME', align: 'right', fixed: true,
					content: 'Give the chart a meaningful name that you\'ll recognize on the dashboard.'
				},
				'wizardSave': {
					id: 'chart_save', title: 'SAVE THE CHART', align: 'right', fixed: true,
					content: 'Click to save the chart and add it to the dashboard.'
				},
				'dashboardChart': {
					title: 'YOUR CHART', align: 'top', emphasize: false,
					content: 'See the chart you\'ve just created.',
					actions: [
						{ title: 'Next', state: 'reports' }
					]
				},
				'reports': {
					id: 'reports', title: 'REPORTING', align: 'right', fixed: true,
					content: 'Reports let you schedule an email with an executive summary.'
				},
				'reportsSchedule': {
					id: 'reports_schedule', title: 'SCHEDULE REPORTING', align: 'right', emphasize: false,
					content: 'Decide how often you\'d like to receive a report.',
					actions: [
						{ title: 'Next', state: 'reportsFrequency' }
					]
				},
				'reportsFrequency': {
					id: 'reports_frequency', title: 'SCHEDULE REPORTING', align: 'right', emphasize: false,
					content: 'Choose between daily, weekly, or monthly reports.',
					actions: [
						{ title: 'Next', state: 'reportsMails' }
					]
				},
				'reportsMails': {
					id: 'reports_mails', title: 'SCHEDULE REPORTING', align: 'right', emphasize: false,
					content: 'Add all email addresses that should receive the report.',
					actions: [
						{ title: 'Next', state: 'reportsDownload'}
					]
				},
				'reportsDownload': {
					id: 'reports_download', title: 'DOWNLOAD REPORT', align: 'right',
					content: 'Click to download a report now.\nThe report is generated at the end of each discovery cycle.',
					actions: [
						{ title: 'SKIP', state: 'tourFinale'}
					]
				},
				'tourFinale': {
					title: 'JUST THE BEGINNING', align: 'center',
					content: 'The tour ends here, but you\'re just getting started. Remember: you can always restart the tour using the icon on the top right corner.',
					actions: [
						{ title: 'OK', state: '' }
					]
				}
			},
			queues: {
				adapters: ['activeDirectory', 'network', 'virtualizationCloud', 'virtualizationLocal',
					'agent', 'agentIT', 'va', 'mdm', 'serviceNowAdapter', 'oktaAdapter', 'csv', 'devices'],
				devices: ['bestDevice', 'query', 'queryResults', 'alerts', 'dashboardBack'],
				alerts: ['alertNew', 'settings'],
				dashboard: ['adapters', 'dashboardManaged', 'dashboardWizard'],
				dashboardWizard: ['wizardIntersect', 'wizardModule', 'wizardMain', 'wizardSecond', 'wizardName']
			}
		}
	},
	mutations: {
		[ UPDATE_EMPTY_STATE ] (state, payload) {
			state.emptyStates = { ...state.emptyStates, ...payload }
		},
		[ START_TOUR ] (state) {
			state.tourStates.active = true
			if (!state.tourStates.current) {
				state.tourStates.current = 'adapters'
			}
		},
		[ CHANGE_TOUR_STATE ] (state, payload) {
			let stateName = payload.name
			if (stateName && state.tourStates.defs[stateName]) {
				let queueName = state.tourStates.defs[stateName].queue
				if (queueName && state.tourStates.queues[queueName]) {
					if (state.tourStates.queues[queueName].includes(stateName)) {
						state.tourStates.queues[queueName] = state.tourStates.queues[queueName].filter(item => item !== stateName)
					} else {
						stateName = state.tourStates.queues[queueName][0]
						state.tourStates.queues[queueName] = state.tourStates.queues[queueName].slice(1)
					}
				}
			}
			state.tourStates.current = stateName
			if (state.tourStates.defs[stateName]) {
				if (payload.id) {
					state.tourStates.defs[stateName].id = payload.id
				}
				if (payload.align) {
					state.tourStates.defs[stateName].align = payload.align
				}
			}
		},
		[ UPDATE_TOUR_STATE ] (state, payload) {
			if (!payload.name || !state.tourStates.defs[payload.name]) return
			if (payload.id) {
				state.tourStates.defs[payload.name].id = payload.id
			}
			if (payload.align) {
				state.tourStates.defs[payload.name].align = payload.align
			}
		},
		[ NEXT_TOUR_STATE ] (state, queueName) {
			let queue = state.tourStates.queues[queueName]
			if (!queue || !queue.length) return
			state.tourStates.current = queue[0]
			state.tourStates.queues[queueName] = queue.slice(1, queue.length)
		},
		[ STOP_TOUR ] (state) {
			state.tourStates.active = false
			state.tourStates.current = ''
		}
	}
}