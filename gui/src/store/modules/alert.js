import { REQUEST_API } from '../actions'

export const FETCH_ALERTS = 'FETCH_ALERTS'
export const UPDATE_ALERTS = 'UPDATE_ALERTS'


export const alert = {
	state: {
		alertList: {fetching: false, data: [], error: ''},
		fields: [
			{ path: 'severity'},
			{ path: 'timestamp', name: 'Date Time', type: 'timestamp', default: true },
			{ path: 'type', name: 'Source', default: true }
		]

	},
	getters: {},
	mutations: {
		[ UPDATE_ALERTS ] (state, payload) {
			state.alertList.fetching = payload.fetching
			if (payload.data) {
				state.alertList.data = [ ...state.alertList.data, ...payload.data ]
			}
			if (payload.error) {
				state.alertList.error = payload.error
			}
		}
	},
	actions: {
		[ FETCH_ALERTS ] ({dispatch}, payload) {
			if (!payload.skip) { payload.skip = 0 }
			/* Getting first page - empty table */
			let param = `?limit=${payload.limit}&skip=${payload.skip}`
			if (payload.filter && Object.keys(payload.filter).length) {
				param += `&filter=${JSON.stringify(payload.filter)}`
			}
			dispatch(REQUEST_API, {
				rule: `api/devices${param}`,
				type: UPDATE_ALERTS
			})
		}
	}
}