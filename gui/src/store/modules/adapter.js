import { REQUEST_API } from '../actions'

export const FETCH_ADAPTERS = 'FETCH_ADAPTERS'
export const UPDATE_ADAPTERS = 'UPDATE_ADAPTERS'

export const adapter = {
	state: {
		/* All adapters */
		adapterList: {fetching: false, data: [
			{status: 'success', state: 'Connected', plugin_name: 'ad_adapter', name: 'Active Directory',
				description: 'Manages Windows devices', connected_servers: 20 }
		], error: ''},
		/* Statically defined fields that should be presented for each adapter, in this order  */
		fields: [
			{path: 'name', name: 'Name', type: 'status-icon-logo-text'},
			{path: 'description', name: 'Description'},
			{path: 'connected_servers', name: 'Connected Servers'},
			{path: 'state', name: 'State'}
		]
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
		}
	}
}