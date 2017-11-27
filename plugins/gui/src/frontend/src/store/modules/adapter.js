import { REQUEST_API } from '../actions'

export const FETCH_ADAPTERS = 'FETCH_ADAPTERS'
export const UPDATE_ADAPTERS = 'UPDATE_ADAPTERS'
export const FETCH_ADAPTER = 'FETCH_ADAPTER'
export const SET_ADAPTER = 'SET_ADAPTER'
export const UPDATE_ADAPTER = 'UPDATE_ADAPTER'
export const UPDATE_ADAPTER_SERVER = 'UPDATE_ADAPTER_SERVER'
export const ADD_ADAPTER_SERVER = 'ADD_ADAPTER_SERVER'

export const adapter = {
	state: {
		/* All adapters */
		adapterList: {
			fetching: false, data: [], error: ''
		},

		/* Statically defined fields that should be presented for each adapter, in this order  */
		adapterFields: [
			{path: 'name', name: 'Name', type: 'status-icon-logo-text'},
			{path: 'description', name: 'Description'},
			{path: 'connected_servers', name: 'Connected Servers'},
			{path: 'state', name: 'State'}
		],

		/* Statically defined fields that should be presented for a single adapter's server */
		serverFields: [
			{path: 'status', name: '', type: 'status'},
			{path: 'name', name: 'Name'},
			{path: 'ip', name: 'IP Address'},
			{path: 'last_updated', name: 'Last Updated', type: 'timestamp'}
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
				state.adapterList.data = [...state.adapterList.data]
				payload.data.forEach((adapter) => {
					state.adapterList.data.push({ ...adapter, id: adapter.unique_plugin_name })
				})
			}
			if (payload.error) {
				state.adapterList.error = payload.error
			}
		},
		[ SET_ADAPTER ] (state, payload) {
			/*
				Called first before API request for a specific adapter, in order to update state to fetching
				Called again after API call returns with either error or data which is assigned to current adapter
			 */
			state.currentAdapter.fetching = payload.fetching
			state.currentAdapter.error = payload.error
			if (payload.data) {
				state.currentAdapter.data = {
					servers: [ ...payload.data ]
				}
			}
		},
		[ ADD_ADAPTER_SERVER ] (state, payload) {
			state.currentAdapter.data = { ...state.currentAdapter.data }
			state.currentAdapter.data.push({ ...payload })
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
			dispatch(REQUEST_API, {
				rule: `api/adapters${param}`,
				type: UPDATE_ADAPTERS
			})
		},
		[ FETCH_ADAPTER ] ({dispatch}, adapterId) {
			/*
				Fetch a single adapter with all its clients and schema and stuff, according to given id
			 */
			if (!adapterId) { return }
			dispatch(REQUEST_API, {
				rule: `api/adapters/${adapterId}/clients`,
				type: SET_ADAPTER
			})
		},
		[ UPDATE_ADAPTER ] ({dispatch}, payload) {
			/*
				Call API to save given adapter data to the given adapter id
			 */
			dispatch(REQUEST_API, {
				rule: `api/adapters/${payload.id}`,
				method: 'POST',
				data: payload
			})
		},
		[ UPDATE_ADAPTER_SERVER ] ({dispatch, commit}, payload) {
			/*
				Call API to save given server data to adapter by the given adapter id,
				either adding a new server or updating and existing one, if id is provided with the data
			 */
			if (!payload || !payload.adapterId || !payload.serverData) { return }
			let rule = `api/adapter/${payload.adapterId}/server`
			if (payload.serverData.id !== 'new') {
				rule += '/' + payload.serverData.id
			}
			dispatch(REQUEST_API, {
				rule: rule,
				method: 'POST',
				data: payload.serverData
			}).then((response) => {
				if (response === '') {
					return
				}
				payload.serverData.id = response
				commit(ADD_ADAPTER_SERVER, payload.serverData)
			})
		}
	}
}