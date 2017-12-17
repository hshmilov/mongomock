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
	'esx_adapter': {
		name: 'ESX',
		description: 'VMware ESXi is an entreprise-class, type-1 hypervisor developed by VMware for deploying and serving virtual computers.'
	},
	'sentinelone_adapter': {
		name: 'SentinelOne',
		description: 'SentinelOne is a next-generation endpoint protection software unifying prevention, detection, and response in a single platform.'
	},
	'epo_adapter': {
		name: 'McAfee',
		description: 'McAfee ePolicy Orchestrator (ePO) is a security management platform that provides real-time monitoring of security solutions.'
	},
	'stresstest_adapter':{
		name: "LOL",
		description: "i am the king of devices"
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
			{path: 'unique_plugin_name', name: '', hidden: true },
			{path: 'plugin_name', name: 'Name', type: 'status-icon-logo-text' },
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
				Called again after API call returns with either error or result data, that is added to adapters list
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
					state.adapterList.data.push({ ...adapter,
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
				Called again after API call returns with either error or data which is assigned to current adapter
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
			state.currentAdapter.data = { ...state.currentAdapter.data }
			state.currentAdapter.data.clients.push({ ...payload })
		},
		[ UPDATE_ADAPTER_SERVER ] (state, payload) {
			state.currentAdapter.data = { ...state.currentAdapter.data }
			state.currentAdapter.data.clients.forEach((client, index) => {
				if (client.uuid === payload.uuid) {
					state.currentAdapter.data.clients[index] = { ...payload }}
			})
		},
		[ REMOVE_SERVER ] (state, serverId) {
			state.currentAdapter.data = { ...state.currentAdapter.data,
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
				Call API to save given server data to adapter by the given adapter id,
				either adding a new server or updating and existing one, if id is provided with the data
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
				if (response !== '') {
					return
				}
				commit(REMOVE_SERVER, payload.serverId)
			})
		}
	}
}