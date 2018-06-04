

export const UPDATE_EMPTY_STATE = 'UPDATE_EMPTY_STATE'

export const START_TOUR = 'START_TOUR'
export const UPDATE_TOUR_STATE = 'NEXT_TOUR_STATE'
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
					id: 'adapters', title: 'PLUG IN YOUR NETWORK', align: 'right',
					content: 'Adapters are the way Axonius pulls device and user information from you systems.\nClick here to see all available adapters.'
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
					content: 'After inserting all required fields correctly, click here to connect to the server.',
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
					id: 'adapters', title: 'PLUG IN YOUR NETWORK', align: 'right',
					content: 'Let\'s return to our Adapters'
				},
				'network': {
					title: 'NETWORK ADAPTERS', align: 'center', queue: 'adapters',
					content: 'Which major Switch/Router is in your environment or next the Axonius instance?',
					actions: [
						{ title: 'Cisco', state: 'cisco' },
						{ title: 'Juniper', state: 'juniper' },
						{ title: 'Fortinet', state: 'fortinet' },
						{ title: 'Other', state: 'networkNone' }
					]
				},
				'cisco': {
					title: 'Cisco ADAPTERS', align: 'center',
					content: 'Which Cisco do you use?',
					actions: [
						{ title: 'Cisco Prime', state: 'ciscoPrime' },
						{ title: 'Cisco Switch/Router', state: 'ciscoRegular' },
						{ title: 'Other', state: 'networkNoCisco'}
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
					content: 'Which other major Switch/Router is in your environment?',
					actions: [
						{ title: 'Juniper', state: 'juniper' },
						{ title: 'Fortinet', state: 'fortinet' },
						{ title: 'Other', state: 'networkNone' }
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
				'networkNone': {
					title: 'NETWORK ADAPTERS', align: 'center',
					content: 'We do not currently support your networking gear.\nYou can get the same info from connecting a VA solution.',
					actions: [
						{ title: 'OK', state: 'va'}
					]
				},
				'virtualizationCloud': {
					title: 'CLOUD PROVIDERS', align: 'center', queue: 'adapters',
					content: 'Which of the following cloud providers do you use most?',
					actions: [
						{ title: 'Amazon Elastic', state: 'aws' },
						{ title: 'Microsoft Azure', state: 'azure' },
						{ title: 'IBM Cloud', state: 'ibmCloud' },
						{ title: 'Other', state: 'virtualizationCloudNone' }
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
				'virtualizationCloudNone': {
					title: 'CLOUD PROVIDERS', align: 'center',
					content: 'We currently do not support your cloud provider.\nLet\'s move forward to virtualization solutions.',
					actions: [
						{ title: 'OK', state: 'virtualizationLocal'}
					]
				},
				'virtualizationLocal': {
					title: 'VIRTUALIZATION SOLUTIONS', align: 'center', queue: 'adapters',
					content: 'Which virtualization solution do you use most?',
					actions: [
						{ title: 'VMWare ESXi', state: 'esx' },
						{ title: 'Hyper-V', state: 'hyperV' },
						{ title: 'OpenStack', state: 'openStack' },
						{ title: 'Oracle VM', state: 'oracleVM' },
						{ title: 'Other', state: 'virualizationLocalNone' }
					]
				},
				'esx': {
					id: 'esx_adapter', title: 'VMWare ESXi ADAPTER', align: 'right',
					content: 'Click here to configure it.'
				},
				'hyperV': {
					id: 'hyper_v_adapter', title: 'Hyper-V ADAPTER', align: 'right',
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
				'virualizationLocalNone': {
					title: 'VIRTUALIZATION SOLUTIONS', align: 'center',
					content: 'We currently do not support your virtualization solution. Let\'s continue.',
					actions: [
						{ title: 'OK', state: 'agent'}
					]
				},
				'agent': {
					title: 'ENDPOINT PROTECTION', align: 'center', queue: 'adapters',
					content: 'Which is the most common Endpoint Protection or EDR Agent you use?',
					actions: [
						{ title: 'McAfee ePO', state: 'epo' },
						{ title: 'Symantec', state: 'symantec' },
						{ title: 'CarbonBlack', state: 'carbonBlack' },
						{ title: 'Minerva', state: 'minerva'},
						{ title: 'enSilo', state: 'enSilo' },
						{ title: 'Secdo', state: 'secdo' },
						{ title: 'SentinelOne', state: 'sentinelOne' },
						{ title: 'Other', state: 'agentIT' },
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
					content: 'Which CarbonBlack product do you use most?',
					actions: [
						{ title: 'Response', state: 'carbonBlackResponse' },
						{ title: 'Protection', state: 'carbonBlackProtection' },
						{ title: 'Defense', state: 'carbonBlackDefense' }
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
					content: 'Which is the most common IT Agent you use?',
					actions: [
						{ title: 'SCCM', state: 'sccm'},
						{ title: 'BigFix', state: 'bigFix'},
						{ title: 'Puppet', state: 'puppet'},
						{ title: 'Chef', state: 'chef'},
						{ title: 'Bomgar', state: 'bomgar'},
						{ title: 'ManageEngine', state: 'manageEngine'},
						{ title: 'Kaseya', state: 'kaseya'},
						{ title: 'ObserveIT', state: 'observeIT'},
						{ title: 'Other', state: 'va'}
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
						{ title: 'Other', state: 'vaNone' }
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
				'vaNone': {
					title: 'VULNERABILITY ASSESSMENT', align: 'center',
					content: 'We do not currently support your vulnerability assessment solution.\nLet\'s continue.',
					actions: [
						{ title: 'OK', state: 'mdm' }
					]
				},
				'mdm': {
					title: 'MDM SOLUTIONS', align: 'center', queue: 'adapters',
					content: 'Which MDM solution do you use most?',
					actions: [
						{ title: 'MobileIron', state: 'mobileIron' },
						{ title: 'VMWare Airwatch', state: 'vmwareAirwatch' },
						{ title: 'Blackberry UEM', state: 'blackberry' },
						{ title: 'Other', state: 'mdmNone' }
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
				'mdmNone': {
					title: 'MDM SOLUTIONS', align: 'center',
					content: 'We do not currently support your MDM solution.\nLet\'s continue.',
					actions: [
						{ title: 'OK', state: 'serviceNow'}
					]
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
					content: ''
				}
			},
			queues: {
				adapters: ['activeDirectory', 'network', 'virtualizationCloud', 'virtualizationLocal',
					'agent', 'agentIT', 'va', 'mdm', 'serviceNow', 'csv', 'devices']
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
		[ UPDATE_TOUR_STATE ] (state, stateName) {
			let queueName = state.tourStates.defs[stateName].queue
			if (queueName && state.tourStates.queues[queueName]) {
				if (state.tourStates.queues[queueName].includes(stateName)) {
					state.tourStates.queues[queueName] = state.tourStates.queues[queueName].filter(item => item !== stateName)
				} else {
					stateName = state.tourStates.queues[queueName][0]
					state.tourStates.queues[queueName] = state.tourStates.queues[queueName].slice(1)
				}
			}
			state.tourStates.current = stateName
		},
		[ STOP_TOUR ] (state) {
			state.tourStates.active = false
			state.tourStates.current = ''
		}
	}
}