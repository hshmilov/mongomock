/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'

export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'


export const devices = {
	state: {
		content: { data: [], fetching: false, error: '', rule: ''},
		count: { data: 0, fetching: false, error: ''},
		view: {
			page: 0, pageSize: 20, fields: [
				'adapters', 'specific_data.data.hostname', 'specific_data.data.name', 'specific_data.data.os.type',
				'specific_data.data.network_interfaces.ips', 'specific_data.data.network_interfaces.mac', 'labels'
			], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
		},
		fields: { data: {}, fetching: false, error: ''},
		views: {
			saved: { data: [], fetching: false, error: ''},
			history: { data: [], fetching: false, error: ''}
		},
		labels: { data: [], fetching: false, error: ''},

		current: {fetching: false, data: {}, error: ''}
	},
	getters: {},
	mutations: {
		[ UPDATE_DEVICE ] (state, payload) {
			state.current.fetching = payload.fetching
			state.current.error = payload.error
			if (payload.data) {
				state.current.data = payload.data
			}
		}
	},
	actions: {
		[ FETCH_DEVICE ] ({dispatch}, deviceId) {
			if (!deviceId) { return }
			dispatch(REQUEST_API, {
				rule: `device/${deviceId}`,
				type: UPDATE_DEVICE
			})
		}
	}
}