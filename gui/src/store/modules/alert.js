import { REQUEST_API } from '../actions'

export const FETCH_ALERTS = 'FETCH_ALERTS'
export const UPDATE_ALERTS = 'UPDATE_ALERTS'
export const FETCH_ALERT = 'FETCH_ALERT'
export const UPDATE_ALERT = 'UPDATE_ALERT'
export const ARCHIVE_ALERT = 'ARCHIVE_ALERT'
export const REMOVE_ALERT = 'REMOVE_ALERT'
export const RESTART_ALERTS = 'RESTART_ALERTS'
export const INSERT_ALERT = 'INSERT_ALERT'
export const ADD_ALERT = 'ADD_ALERT'


export const alert = {
	state: {
		alertList: {fetching: false, data: [], error: ''},
		fields: [
			{ path: 'name', name: 'Name', selected: true, default: true, control: 'text'},
			{ path: 'timestamp', name: 'Date Time', type: 'timestamp', selected: true, default: true },
			{ path: 'type', name: 'Triggered', selected: true, default: true }
		],
		currentAlert: { fetching: false, data: {}, error: '' }
	},
	getters: {},
	mutations: {
		[ UPDATE_ALERTS ] (state, payload) {
			state.alertList.fetching = payload.fetching
			if (payload.data) {
				let processedData = []
				payload.data.forEach(function(alert) {
					processedData.push({ ...alert, type: 'Manual'})
				})
				state.alertList.data = [ ...state.alertList.data, ...processedData ]
			}
			if (payload.error) {
				state.alertList.error = payload.error
			}
		},
		[ UPDATE_ALERT ] (state, payload) {
			state.currentAlert.fetching = payload.fetching
			if (payload.data) {
				state.currentAlert.data = { ...payload.data }
			}
			if (payload.error) {
				state.currentAlert.error = payload.error
			}
		},
		[ REMOVE_ALERT ] (state, payload) {
			state.alertList.data = [ ...state.alertList.data ].filter(function(alert) {
				return alert.id !== payload
			})
		},
		[ ADD_ALERT ] (state, payload) {
			state.alertList.data = [{
				...payload, 'timestamp': new Date().getTime()
			}, ...state.alertList.data ]
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
				rule: `api/alerts${param}`,
				type: UPDATE_ALERTS
			})
		},
		[ FETCH_ALERT ] ({dispatch}, alertId) {
			if (!alertId) { return }
			dispatch(REQUEST_API, {
				rule: `api/alerts/${alertId}`,
				type: UPDATE_ALERT
			})
		},
		[ ARCHIVE_ALERT ] ({dispatch, commit}, alertId) {
			if (!alertId) { return }
			dispatch(REQUEST_API, {
				rule: `api/alerts/${alertId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response !== '') {
					return
				}
				commit(REMOVE_ALERT, alertId)
			})
		},
		[ INSERT_ALERT ] ({dispatch, commit}, payload) {
			if (!payload) { return }
			let rule = 'api/alerts'
			if (payload.id !== 'new') {
				rule += '/' + payload.id
			}
			dispatch(REQUEST_API, {
				rule: rule,
				method: 'POST',
				data: payload
			}).then((response) => {
				if (response === '') {
					return
				}
				payload.id = response
				commit(ADD_ALERT, payload)
			})
		}
	}
}