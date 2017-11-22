import { REQUEST_API } from '../actions'

export const FETCH_ADAPTERS = 'FETCH_ADAPTERS'
export const UPDATE_ADAPTERS = 'UPDATE_ADAPTERS'
export const FETCH_ADAPTER = 'FETCH_ADAPTER'
export const SET_ADAPTER = 'SET_ADAPTER'
export const UPDATE_ADAPTER = 'UPDATE_ADAPTER'

export const adapter = {
	state: {
		/* All adapters */
		adapterList: {fetching: false, data: [
			{status: 'success', state: 'Connected', id: 'ad_adapter_123', type: 'ad_adapter', name: 'Active Directory',
				description: 'Manages Windows devices', connected_servers: 20 }
		], error: ''},
		/* Statically defined fields that should be presented for each adapter, in this order  */
		fields: [
			{path: 'name', name: 'Name', type: 'status-icon-logo-text'},
			{path: 'description', name: 'Description'},
			{path: 'connected_servers', name: 'Connected Servers'},
			{path: 'state', name: 'State'}
		],
		currentAdapter: { fetching: false, data: {
			id: 'ad_adapter',
			name: 'Active Directory',
			fields: [
				{ path: 'status', name: '', type: 'status-icon'},
				{ path: 'name', name: 'Name'},
				{ path: 'ip', name: 'IP Address'},
				{ path: 'last_updated', name: 'Last Updated', type: 'timestamp'}
			],
			servers: [
				{ status: 'success', name: 'DC-Main', ip: '192.168.4.1', last_updated: new Date().getTime()},
				{ status: 'error', name: 'DC-Secondary', ip: '192.168.4.2', last_updated: new Date().getTime()},
				{ status: 'warning', name: 'DC-Secondary', ip: '192.168.4.3', last_updated: new Date().getTime()}
			]
		}, error: ''}
	},
	getters: {},
	mutations: {
		[ UPDATE_ADAPTERS ] (state, payload) {
			state.adapterList.fetching = payload.fetching
			if (payload.data) {
				state.adapterList.data = [ ...state.adapterList.data, ...payload.data ]
			}
			if (payload.error) {
				state.adapterList.error = payload.error
			}
		},
		[ SET_ADAPTER ] (state, payload) {
			state.currentAdapter.fetching = payload.fetching
			state.currentAdapter.error = payload.error
			if (payload.data) {
				state.currentAdapter.data = { ...payload.data }
			}
		}
	},
	actions: {
		[ FETCH_ADAPTERS ] ({dispatch}, payload) {
			/*
				Fetch a page of limit number of adapters, starting from number skip
				If skip is not provided, start from first
				If limit is not provided, take remaining until the end
			 */
			if (!payload) { payload = {} }
			if (!payload.limit) { payload.limit = -1 }
			if (!payload.skip) { payload.skip = 0 }
			let param = `?skip=${payload.skip}&limit=${payload.limit}`
			if (payload.filter) {
				param += `&filter=${JSON.stringify(payload.filter)}`
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
				rule: `api/adapters/${adapterId}`,
				type: SET_ADAPTER
			})
		},
		[ UPDATE_ADAPTER ] ({dispatch}, payload) {
			dispatch(REQUEST_API, {
				rule: `api/adapters/${payload.id}`,
				method: 'POST',
				data: payload
			})
		}
	}
}