import { REQUEST_API } from '../actions'

export const FETCH_ADAPTERS = 'FETCH_ADAPTERS'
export const UPDATE_ADAPTERS = 'UPDATE_ADAPTERS'
export const FETCH_ADAPTER_SERVERS = 'FETCH_ADAPTER_SERVERS'
export const SET_ADAPTER_SERVERS = 'SET_ADAPTER_SERVERS'
export const SAVE_ADAPTER_SERVER = 'SAVE_ADAPTER_SERVER'
export const ADD_ADAPTER_SERVER = 'ADD_ADAPTER_SERVER'
export const UPDATE_ADAPTER_SERVER = 'UPDATE_ADAPTER_SERVER'
export const ARCHIVE_SERVER = 'ARCHIVE_SERVER'
export const REMOVE_SERVER = 'REMOVE_SERVER'

export const adapterStaticData = {
	'ad_adapter': {
		name: 'Active Directory',
		description: 'Active Directory (AD) is a directory service for Windows domain networks that authenticate and authorizes all users and computers.'
	},
	'aws_adapter': {
		name: 'Amazon Elastic',
		description: 'Amazon Elastic Compute Cloud (Amazon EC2) provides scalable computing capacity in the Amazon Web Services (AWS) cloud.'
	},
	'jamf_adapter': {
		name: 'Jamf Pro',
		description: 'Jamf Pro is an enterprise mobility management (EMM) tool that provides unified endpoint management for Apple devices.'
	},
	'epo_adapter': {
		name: 'McAfee ePO',
		description: 'McAfee ePolicy Orchestrator (ePO) is a security management platform that provides real-time monitoring of security solutions.'
	},
	'puppet_adapter': {
		name: 'Puppet',
		description: 'Puppet is an open-source software configuration management tool.'
	},
	'qualys_adapter': {
		name: 'Qualys Cloud Platform',
		description: 'The Qualys Cloud Platform monitors customers\' global security and compliance posture using sensors.'
	},
	'qualys_scans_adapter': {
		name: 'Qualys Cloud Platform - Scanner',
		description: 'The Qualys Cloud Platform monitors customers\' global security and compliance posture using sensors.'
	},
	'nexpose_adapter': {
		name: 'Rapid7 Nexpose',
		description: 'Rapid7 Nexpose is a vulnerability management solution, including discovery, detection, verification, risk classification, impact analysis, reporting and mitigation.'
	},
	'sentinelone_adapter': {
		name: 'SentinelOne',
		description: 'SentinelOne is an endpoint protection software including prevention, detection, and response.'
	},
	'splunk_nexpose_adapter': {
		name: 'Splunk <> Rapid7 Nexpose',
		description: 'The Splunk adapter for Rapid7 Nexpose leverages controls from Splunk instances that receive alerts from Rapid7 Nexpose.'
	},
	'splunk_symantec_adapter': {
		name: 'Splunk <> Symantec Endpoint Protection Manager',
		description: 'The Splunk adapter for Symantec Endpoint Protection Manager leverages controls from Splunk instances that receive alerts from Symantec Endpoint Protection Manager.'
	},
	'symantec_adapter': {
		name: 'Symantec Endpoint Protection Manager',
		description: 'Symantec Endpoint Protection Manager manages events, policies, and registration for the client computers that connect to customer networks.'
	},
	'nessus_adapter': {
		name: 'Tenable Nessus',
		description: 'Tenable Nessus is a vulnerability scanning platform for auditors and security analysts.'
	},
	'esx_adapter': {
		name: 'VMware ESXi',
		description: 'VMware ESXi is an entreprise-class, type-1 hypervisor for deploying and serving virtual computers. '
	},
	'cisco_adapter': {
		name: 'Cisco CSR',
		description: 'Cisco Cloud Services Router (CSR) provides routing, security, and network management with multitenancy.'
	},
	'eset_adapter': {
		name: 'ESET Endpoint Security',
		description: 'ESET Endpoint Security is an anti-malware suite for Windows with web filter, firewall, and USB drive and botnet protection.'
	},
	'traiana_lab_machines_adapter': {
		name: 'Traiana Lab Machines',
		description: 'Traiana Lab Machines is a propriatery adapter for Traiana, which queries for new devices from the lab machines inventory.'
	},
	'fortigate_adapter': {
		name: 'Fortinet FortiGate',
		description: 'FortiGate Next-Generation firewall provides high performance, multilayered validated security and visibility for end-to-end protection across the entire enterprise network.'
	},
	'qcore_adapter': {
		name: 'Qcore adapter',
		description: 'Qcore medical pumps adapter (Saphire+ 14.5)'
	},
	'sccm_adapter': {
		name: 'Microsoft SCCM',
		description: 'Microsoft System Center Configuration Manager (SCCM) uses on-premises Configuration Manager or Microsoft Exchange to manage PCs, servers and devices.'
	},
	'desktop_central_adapter':{
		name: 'ManageEngine Desktop Central',
		description: 'Desktop Central is a Desktop Management and Mobile Device' +
		' Management Software for managing desktops in LAN and across WAN and mobile devices from a central location\n'
	},
	'forcepoint_csv_adapter': {
		name: 'Forcepoint Web Security Endpoint',
		description: 'Forcepoint Web Security Endpoint enables end users to authenticate and' +
		' receive policy enforcement via the Forcepoint Web Security Cloud cloud infrastructure.'
	},
	'csv_adapter': {
		name: 'Serials CSV Adapter',
		description: 'The Serials CSV Adapter is able to import .csv files with inventory information including the serial number of a device and supplemental device data.'
	},
	'minerva_adapter': {
		name: 'Minerva Labs Endpoint Malware Vaccination',
		description: 'Minerva Labs Endpoint Malware Vaccination enables incident response teams' +
		' to immunize endpoints to neutralize attacks. By simulating infection markers, rather than creating them, Minerva contains outbreaks that bypass AV tools.'
	},
	'juniper_adapter': {
        name: 'Juniper Junos Space',
        description: 'Junos Space Network Management Platform simplifies and automates management of Juniper’s switching, routing, and security devices.'
    },
	'bomgar_adapter': {
		name: 'Bomgar Adapter',
		description: 'Bomgar is a remote support solution that allows support technicians to remotely connect to end-user systems through firewalls from their computer or mobile device.'
	},
	'bigfix_adapter': {
		name: 'IBM Bigfix',
		description: 'IBM Bigfix is a systems-management software product developed by IBM for managing large groups of computers.'
	}
}

export const adapter = {
	state: {
		/* All adapters */
		adapterList: {
			fetching: false, data: [], error: ''
		},

		/* Statically defined fields that should be presented for each adapter, in this order  */
		adapterFields: [
			{path: 'unique_plugin_name', name: '', hidden: true},
			{path: 'plugin_name', name: 'Name', type: 'status-icon-logo-text'},
			{path: 'description', name: 'Description'},
			{path: 'status', name: '', hidden: true}
		],

		/* Data about a specific adapter that is currently being configured */
		currentAdapter: {
			fetching: false, data: {}, error: ''
		}
	},
	getters: {},
	mutations: {
		[ UPDATE_ADAPTERS ] (state, payload) {
			/*
				Called first before API request for adapters, in order to update state to fetching
				Called again after API call returns with either error or result controls, that is added to adapters list
			 */
			state.adapterList.fetching = payload.fetching
			if (payload.data) {
				state.adapterList.data = []
				payload.data.forEach((adapter) => {
					let pluginText = adapter.plugin_name
					let pluginDescription = ''
					if (adapterStaticData[adapter.plugin_name]) {
						pluginText = adapterStaticData[adapter.plugin_name].name
						pluginDescription = adapterStaticData[adapter.plugin_name].description
					}
					state.adapterList.data.push({
						...adapter,
						id: adapter.unique_plugin_name,
						plugin_name: {
							text: pluginText,
							logo: adapter.plugin_name,
							status: adapter.status
						},
						description: pluginDescription
					})
				})
			}
			if (payload.error) {
				state.adapterList.error = payload.error
			}
		},
		[ SET_ADAPTER_SERVERS ] (state, payload) {
			/*
				Called first before API request for a specific adapter, in order to update state to fetching
				Called again after API call returns with either error or controls which is assigned to current adapter
			 */
			state.currentAdapter.fetching = payload.fetching
			state.currentAdapter.error = payload.error
			if (payload.data) {
				state.currentAdapter.data = {
					...state.currentAdapter.data, ...payload.data,
					clients: payload.data.clients.map((client) => {
						client['date_fetched'] = undefined
						return client
					})
				}

			}
		},
		[ ADD_ADAPTER_SERVER ] (state, payload) {
			state.currentAdapter.data = {...state.currentAdapter.data}
			state.currentAdapter.data.clients.push({...payload})
		},
		[ UPDATE_ADAPTER_SERVER ] (state, payload) {
			state.currentAdapter.data = {...state.currentAdapter.data}
			state.currentAdapter.data.clients.forEach((client, index) => {
				if (client.uuid === payload.uuid) {
					state.currentAdapter.data.clients[index] = {...payload}
				}
			})
		},
		[ REMOVE_SERVER ] (state, serverId) {
			state.currentAdapter.data = {
				...state.currentAdapter.data,
				clients: state.currentAdapter.data.clients.filter((server) => {
					return server.uuid !== serverId
				})
			}
		}
	},
	actions: {
		[ FETCH_ADAPTERS ] ({dispatch}, payload) {
			/*
				Fetch all adapters, according to given filter
			 */
			let param = ''
			if (payload && payload.filter) {
				param = `?filter=${JSON.stringify(payload.filter)}`
			}
			return dispatch(REQUEST_API, {
				rule: `/api/adapters${param}`,
				type: UPDATE_ADAPTERS
			})
		},
		[ FETCH_ADAPTER_SERVERS ] ({dispatch}, adapterId) {
			/*
				Fetch a single adapter with all its clients and schema and stuff, according to given id
			 */
			if (!adapterId) { return }
			dispatch(REQUEST_API, {
				rule: `/api/adapters/${adapterId}/clients`,
				type: SET_ADAPTER_SERVERS
			})
		},
		[ SAVE_ADAPTER_SERVER ] ({dispatch}, payload) {
			/*
				Call API to save given server controls to adapter by the given adapter id,
				either adding a new server or updating and existing one, if id is provided with the controls
			 */
			if (!payload || !payload.adapterId || !payload.serverData) { return }
			let rule = `/api/adapters/${payload.adapterId}/clients`
			if (payload.uuid !== 'new') {
				rule += '/' + payload.uuid
			}
			dispatch(REQUEST_API, {
				rule: rule,
				method: 'PUT',
				data: payload.serverData
			}).then(() => {
				dispatch(FETCH_ADAPTER_SERVERS, payload.adapterId)
			})
		},
		[ ARCHIVE_SERVER ] ({dispatch, commit}, payload) {
			if (!payload.adapterId || !payload.serverId) { return }
			dispatch(REQUEST_API, {
				rule: `/api/adapters/${payload.adapterId}/clients/${payload.serverId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response.data !== '') {
					return
				}
				commit(REMOVE_SERVER, payload.serverId)
			})
		}
	}
}
