

export const UPDATE_EMPTY_STATE = 'UPDATE_EMPTY_STATE'

export const START_TOUR = 'START_TOUR'
export const CHANGE_TOUR_STATE = 'CHANGE_TOUR_STATE'
export const UPDATE_TOUR_STATE = 'UPDATE_TOUR_STATE'
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
					id: 'adapters', title: 'CONNECT YOUR NETWORK', align: 'right',
					content: 'Axonius uses Adapters to collect and correlate device and user information from your systems.'
				},
				'activeDirectory': {
					id: 'active_directory_adapter', title: 'ActiveDirectory ADAPTER', queue: 'adapters', align: 'right',
					content: 'If you use ActiveDirectory, click here to configure it.'
				},
				'addServer': {
					id: 'new_server', title: 'CONFIGURE YOUR SERVER', align: 'left',
					content: 'This adapter can connect to any server you have credentials for.\nClick here to fill them in.'
				},
				'saveServer': {
					id: 'save_server', title: 'SAVE CREDENTIALS', align: 'right',
					content: 'Fill in all required fields, then click here to connect the server.',
				},
				'successServer': {
					id: 'status_server', title: 'YOUR SERVER CONNECTED', align: 'bottom',
					content: 'This indicates that the server was added, as Axonius was able connect to it.',
					actions: [
						{ title: 'Next', state: 'backAdapters' }
					]
				},
				'errorServer': {
					id: 'status_server', title: 'PROBLEM WITH CREDENTIALS', align: 'bottom',
					content: 'The red exclamation mark indicates that connection to the server could not be established.\nClick here to view the error and try again.',
				},
				'backAdapters': {
					id: 'adapters', title: 'CONNECT YOUR NETWORK', align: 'right',
					content: 'Let\'s return to our Adapters'
				},
				'network': {
					title: 'NETWORK ADAPTERS', align: 'center', queue: 'adapters',
					content: 'Which of the following switches/routers do you use most?',
					actions: [
						{ title: 'Cisco', state: 'cisco' },
						{ title: 'Juniper', state: 'juniper' },
						{ title: 'Fortinet', state: 'fortinet' },
						{ title: 'SKIP', state: 'virtualizationCloud' }
					]
				},
				'cisco': {
					title: 'CISCO ADAPTERS', align: 'center',
					content: 'Which Cisco management solution do you use?',
					actions: [
						{ title: 'Cisco Prime', state: 'ciscoPrime' },
						{ title: 'Cisco Switch/Router (no management solution)', state: 'ciscoRegular' },
						{ title: 'SKIP', state: 'networkNoCisco'}
					]
				},
				'ciscoPrime': {
					id: 'cisco_prime_adapter', title: 'Cisco Prime ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'ciscoRegular': {
					id: 'cisco_adapter', title: 'Cisco ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'networkNoCisco': {
					title: 'NETWORK ADAPTERS', align: 'center',
					content: 'Which other major switch/router do you use?',
					actions: [
						{ title: 'Juniper', state: 'juniper' },
						{ title: 'Fortinet', state: 'fortinet' },
						{ title: 'SKIP', state: 'virtualizationCloud' }
					]
				},
				'juniper': {
					id: 'juniper_adapter', title: 'Juniper Junos ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'fortinet': {
					id: 'fortigate_adapter', title: 'Fortinet Fortigate ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'virtualizationCloud': {
					title: 'CLOUD PROVIDERS', align: 'center', queue: 'adapters',
					content: 'Which of the following cloud providers do you use most?',
					actions: [
						{ title: 'Amazon Elastic', state: 'aws' },
						{ title: 'Microsoft Azure', state: 'azure' },
						{ title: 'IBM Cloud', state: 'ibmCloud' },
						{ title: 'SKIP', state: 'virtualizationLocal' }
					]
				},
				'aws': {
					id: 'aws_adapter', title: 'Amazon Elastic ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'azure': {
					id: 'azure_adapter', title: 'Microsoft Azure ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'ibmCloud': {
					id: 'softlayer_adapter', title: 'IBM Cloud ADAPTER', align: 'right',
					content: 'Click here to configure it.'
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
					content: 'Click here to configure it.'
				},
				'hyperV': {
					id: 'hyper_v_adapter', title: 'Microsoft Hyper-V ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'openStack': {
					id: 'openstack_adapter', title: 'OpenStack ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'oracleVM': {
					id: 'oracle_vm', title: 'Oracle VM ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'agent': {
					title: 'ENDPOINT PROTECTION', align: 'center', queue: 'adapters',
					content: 'Which is the most common Endpoint Protection or EDR Agent you use?',
					actions: [
						{ title: 'CarbonBlack', state: 'carbonBlack' },
						{ title: 'enSilo', state: 'enSilo' },
						{ title: 'McAfee ePO', state: 'epo' },
						{ title: 'Minerva Labs', state: 'minerva'},
						{ title: 'Secdo', state: 'secdo' },
						{ title: 'SentinelOne', state: 'sentinelOne' },
						{ title: 'Symantec', state: 'symantec' },
						{ title: 'SKIP', state: 'agentIT' }
					]
				},
				'epo': {
					id: 'epo_adapter', title: 'McAfee ePO', align: 'right',
					content: 'Click here to configure it.'
				},
				'symantec': {
					id: 'symantec_adapter', title: 'Symantec ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'carbonBlack': {
					title: 'CarbonBlack', align: 'center',
					content: 'Which Carbon Black product do you use most?',
					actions: [
						{ title: 'Cb Response', state: 'carbonBlackResponse' },
						{ title: 'Cb Protection', state: 'carbonBlackProtection' },
						{ title: 'Cb Defense', state: 'carbonBlackDefense' }
					]
				},
				'carbonBlackResponse': {
					id: 'carbonblack_response_adapter', title: 'CarbonBlack Response ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'carbonBlackProtection': {
					id: 'carbonblack_protection_adapter', title: 'CarbonBlack Protection ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'carbonBlackDefense': {
					id: 'carbonblack_defense_adapter', title: 'CarbonBlack Defense ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'minerva': {
					id: 'minerva_adapter', title: 'Minerva Labs ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'enSilo': {
					id: 'ensilo_adapter', title: 'enSilo Endpoint Protection', align: 'right',
					content: 'Click here to configure it.'
				},
				'secdo': {
					id: 'secdo_adapter', title: 'Secdo Endpoint Protection', align: 'right',
					content: 'Click here to configure it.'
				},
				'sentinelOne': {
					id: 'sentinelone_adapter', title: 'SentinelOne', align: 'right',
					content: 'Click here to configure it.'
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
						{ title: 'SKIP', state: 'va'}
					]
				},
				'sccm': {
					id: 'sccm_adapter', title: 'Microsoft SCCM ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'bigFix': {
					id: 'bigfix_adapter', title: 'IBM Bigfix ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'puppet': {
					id: 'puppet_adapter', title: 'Puppet ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'chef': {
					id: 'chef_adapter', title: 'Chef ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'bomgar': {
					id: 'bomgar_adapter', title: 'Bomgar Remote Support ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'manageEngine': {
					id: 'desktop_central_adapter', title: 'ManageEngine Desktop Central ADAPTER', align: 'bottom',
					content: 'Click here to configure it.'
				},
				'kaseya': {
					id: 'kaseya_adapter', title: 'Kaseya VSA ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'observeIT': {
					id: 'observeit_csv_adapter', title: 'ObserveIT ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'va':  {
					title: 'VULNERABILITY ASSESSMENT', align: 'center', queue: 'adapters',
					content: 'Which Vulnerability Assessment solution do you use?',
					actions: [
						{ title: 'Qualys', state: 'qualys' },
						{ title: 'Rapid7 Nexpose', state: 'nexpose' },
						{ title: 'Tenable Nessus', state: 'nessus' },
						{ title: 'SKIP', state: 'mdm' }
					]
				},
				'qualys': {
					id: 'qualys_scans_adapter', title: 'Qualys Scanner ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'nexpose': {
					id: 'nexpose_adapter', title: 'Rapid7 Nexpose', align: 'right',
					content: 'Click here to configure it.'
				},
				'nessus': {
					id: 'nessus_adapter', title: 'Tenable Nessus ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'mdm': {
					title: 'MDM SOLUTIONS', align: 'center', queue: 'adapters',
					content: 'Which MDM solution do you use most?',
					actions: [
						{ title: 'Blackberry UEM', state: 'blackberry' },
						{ title: 'MobileIron', state: 'mobileIron' },
						{ title: 'VMWare Airwatch', state: 'vmwareAirwatch' },
						{ title: 'Blackberry UEM', state: 'blackberry' },
						{ title: 'SKIP', state: 'serviceNow' }
					]
				},
				'mobileIron': {
					id: 'mobileiron_adapter', title: 'MobileIron EMM ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'vmwareAirwatch': {
					id: 'airwatch_adapter', title: 'VMWare Airwatch', align: 'right',
					content: 'Click here to configure it.'
				},
				'blackberry': {
					id: 'blackberry_uem_adapter', title: 'Blackberry UEM', align: 'right',
					content: 'Click here to configure it.'
				},
				'serviceNow': {
					id: 'service_now_adapter', title: 'ServiceNow ADAPTER', align: 'right', queue: 'adapters',
					content: 'If you use ServiceNow, click here to configure it.'
				},
				'csv': {
					id: 'csv_adapter', title: 'CSV Serials ADAPTER', align: 'right', queue: 'adapters',
					content: 'If you have a CSV with other devices you want to add, click here.'
				},
				'devices': {
					id: 'devices', title: 'SEE YOUR COLLECTED DEVICES', align: 'right',
					content: 'Devices combine data from as many adapters as Axonius found it, according to the correlation rules.'
				},
				'bestDevice': {
					title: 'DEVICE VIEW', align: 'bottom', queue: 'devices',
					content: 'Click here to view in-depth details about this device.'
				},
				'adapterDevice': {
					title: 'DEVICE ADAPTER', align: 'top',
					content: 'Here you see one Adapter\'s data of the device.\nThe fields are specific properties Axonius collects using this Adapter.',
					actions: [
						{ title: 'Next', state: 'otherAdapterDevice'}
					]
				},
				'otherAdapterDevice': {
					title: 'DEVICE ADAPTER',
					content: 'You will see a tab per Adapter that has data about the device.',
					actions: [
						{ title: 'Next', state: 'backDevices'}
					]
				},
				'backDevices': {
					id: 'devices', title: 'DEVICES', align: 'right',
					content: 'Let\'s return to our Devices.'
				},
				'query': {
					id: 'query_wizard', title: 'QUERY', align: 'left', queue: 'devices',
					content: 'Let\'s query devices by their operating system.\nClick here to build the query.'
				},
				'queryField': {
					id: 'query_field', title: 'SELECT FIELD', align: 'left',
					content: 'Click here and select the field "OS Type".\nYou can search for it, if needed.'
				},
				'queryOp': {
					id: 'query_op', title: 'SELECT OPERATOR', align: 'left',
					content: 'Click here and select the operator "equals" to compare to a value.'
				},
				'queryValue': {
					id: 'query_value', title: 'SELECT VALUE', align: 'left',
					content: 'Click here and select the OS you would like to find.'
				},
				'queryResults': {
					title: 'QUERY RESULTS', align: 'center', queue: 'devices',
					content: 'You can notice the content of the table changed to show the results of your query.\nYou can continue refining the query.',
					actions: [
						{ title: 'Next', state: 'querySave' }
					]
				},
				'querySave': {
					id: 'query_save', title: 'SAVE QUERY', align: 'bottom',
					content: 'Click here to save this query by a name.'
				},
				'querySaveConfirm': {
					id: 'query_save_confirm', title: 'SAVE QUERY', align: 'right',
					content: 'Fill in a name, then click here to save.'
				},
				'queryList': {
					id: 'query_list', title: 'QUERIES LIST', align: 'bottom',
					content: 'Click here to view the saved queries as well as query history.'
				},
				'querySelect': {
					id: 'query_select', title: 'SELECT A QUERY', align: 'bottom',
					content: 'You see here the query you saved, as well as predefined queries for significant properties of AD.\nSelect a query to execute it and load the results.'
				},
				'alerts': {
					id: 'alerts', title: 'DEFINE ALERTS', align: 'right', queue: 'devices',
					content: 'Alerts monitor results of queries and perform actions accordingly.'
				},
				'alertNew': {
					id: 'alert_new', title: 'NEW ALERT', align: 'left', queue: 'alerts',
					content: 'Let\'s create an alert for the query we saved.\nClick here to start.'
				},
				'alertName': {
					id: 'alert_name', title: 'ALERT NAME', align: 'right',
					content: 'Give the alert a name, by which you can find it in the table of alerts.'
				},
				'alertQuery': {
					id: 'alert_query', title: 'ALERT QUERY', align: 'right',
					content: 'Select the name by which you saved the query previously.'
				},
				'alertIncreased': {
					id: 'alert_increased', title: 'ALERT TRIGGER', align: 'right',
					content: 'The change to monitor in the selected query.\nSelect this to check for new added results.'
				},
				'alertAbove': {
					id: 'alert_above', title: 'ALERT TRIGGER', align: 'bottom',
					content: 'The number of new results above which to act.\nEnter 1 to be notified about 2 new results.'
				},
				'alertAction': {
					id: 'alert_notification', title: 'ALERT ACTION', align: 'right',
					content: 'The action to run when alert is triggered.\nSelect this to get a notification (added to the bell on the top bar).'
				},
				'alertSave': {
					id: 'alert_save', title: 'SAVE THE ALERT', align: 'left',
					content: 'Click here to save.'
				},
				'settings': {
					id: 'settings', title: 'SETTINGS', align: 'bottom', queue: 'alerts',
					content: 'Settings allow configuring properties of the system functionality or the UI.'
				}
			},
			queues: {
				adapters: ['activeDirectory', 'network', 'virtualizationCloud', 'virtualizationLocal',
					'agent', 'agentIT', 'va', 'mdm', 'serviceNow', 'csv', 'devices'],
				devices: ['bestDevice', 'query', 'queryResults', 'alerts'],
				alerts: ['alertNew', 'settings']
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
			if (stateName) {
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
		[ STOP_TOUR ] (state) {
			state.tourStates.active = false
			state.tourStates.current = ''
		}
	}
}