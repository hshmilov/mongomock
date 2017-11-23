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
			fetching: false, data: [
				{
					status: 'success',
					state: 'Connected',
					id: 'ad_adapter_123',
					type: 'ad_adapter',
					name: 'Active Directory',
					description: 'Manages Windows devices',
					connected_servers: 20
				}
			], error: ''
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
			fetching: false, data: {
				id: 'ad_adapter_123',
				plugin_name: 'ad_adapter',
				name: 'Active Directory',
				schema: [
					{path: 'username', name: 'User Name', control: 'text'},
					{path: 'password', name: 'Password', control: 'password'}
				],
				servers: [
					{
						id: 1,
						status: 'success',
						name: 'DC-Main',
						ip: '192.168.4.1',
						last_updated: new Date().getTime(),
						username: 'Shira',
						password: 'Gold'
					},
					{
						id: 2,
						status: 'error',
						name: 'DC-Secondary',
						ip: '192.168.4.2',
						last_updated: new Date().getTime(),
						username: 'Noa',
						password: 'Gold'
					},
					{
						id: 3,
						status: 'warning',
						name: 'DC-Secondary',
						ip: '192.168.4.3',
						last_updated: new Date().getTime(),
						username: 'Elah',
						password: 'Gold'
					}
				]
			}, error: ''
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
				state.adapterList.data = [...state.adapterList.data, ...payload.data]
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
				state.currentAdapter.data = {...payload.data}
			}
		},
		[ ADD_ADAPTER_SERVER ] (state, payload) {

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
			/*
				Call API to save given adapter data to the given adapter id
			 */
			dispatch(REQUEST_API, {
				rule: `api/adapters/${payload.id}`,
				method: 'POST',
				data: payload
			})
		}
	}
}