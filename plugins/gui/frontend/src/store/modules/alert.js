import { REQUEST_API } from '../actions'

export const FETCH_ALERTS = 'FETCH_ALERTS'
export const UPDATE_ALERTS = 'UPDATE_ALERTS'
export const RESTART_ALERTS = 'RESTART_ALERTS'
export const SET_ALERT = 'SET_ALERT'
export const ARCHIVE_ALERT = 'ARCHIVE_ALERT'
export const REMOVE_ALERT = 'REMOVE_ALERT'
export const RESTART_ALERT = 'RESTART_ALERT'
export const UPDATE_ALERT = 'UPDATE_ALERT'
export const ADD_ALERT = 'ADD_ALERT'
export const SAVE_ALERT = 'SAVE_ALERT'
export const UPDATE_ALERT_QUERY = 'UPDATE_ALERT_QUERY'

const newAlert = {
	id: 'new',
	name: '',
	triggers: {
		increase: false,
		decrease: false,
		no_change: false,
		above: 0,
		below: 0
	},
	actions: [],
	query: '',
	retrigger: true,
	triggered: false,
	severity: 'info'
}

export const alert = {
	state: {
		/* All alerts */
		alertList: {fetching: false, data: [], error: ''},
		/* Statically defined fields that should be presented for each alert, in this order */
		fields: [
			{ path: 'name', name: 'Name', default: true, control: 'text'},
			{ path: 'report_creation_time', name: 'Creation Time', type: 'timestamp', default: true, control: 'text' },
			{ path: 'message', name: 'Alert Info', default: true },
			{ path: 'severity', name: 'Severity', default: true, type: 'status' }
		],
		/* Data of alert currently being configured */
		alertDetails: { fetching: false, data: { ...newAlert }, error: '' }
	},
	getters: {
		filterFields(state) {
			return state.fields.filter((field) => {
				return field.control !== undefined
			})
		}
	},
	mutations: {
		[ RESTART_ALERTS ] (state) {
			state.alertList.data = []
		},
		[ UPDATE_ALERTS ] (state, payload) {
			/*
				Called once before AJAX call is made, just to update that fetching has started.
				Called again either with error, if call threw an error or with response, if was returned from call.
				The controls is expected to be a list of alerts to be added to current list
				(called for each page, until all controls is collected)
				If there is need to re-fetch, list should be restarted first
			 */
			state.alertList.fetching = payload.fetching
			if (payload.data) {
				let processedData = []
				payload.data.forEach(function(alert) {
					let message = 'No change detected'
					if (alert.triggered) {
						/* Condition was met - updating to informative message, according to criterias */
						message = 'Action triggered on last query result'
					}
					processedData.push({ ...alert,
						id: alert.uuid,
						message: message
					})
				})
				state.alertList.data = payload.restart? processedData : [ ...state.alertList.data, ...processedData ]
			}
			if (payload.error) {
				state.alertList.error = payload.error
			}
		},
		[ SET_ALERT ] (state, alertId) {
			/*
				The controls is expected to be fields and values of a specific alert and is stored for use in the
				alert configuration page
			 */
			if (!alertId) { return }
			state.alertList.data.forEach((alert) => {
				if (alert.uuid === alertId) {
					state.alertDetails.data = alert
				}
			})
		},
		[ REMOVE_ALERT ] (state, payload) {
			/*
				Filter current list of queries so it no longer has an object by the id of given payload
			 */
			state.alertList.data = [ ...state.alertList.data ].filter(function(alert) {
				return alert.id !== payload
			})
		},
		[ ADD_ALERT ] (state, payload) {
			/*
				Add given payload as an object in the beginning of the current alert list
			 */
			state.alertList.data = [{
				...payload, 'timestamp': new Date().getTime(),
				type: 'User defined by: Administrator'
			}, ...state.alertList.data ]
		},
		[ SAVE_ALERT ] (state, payload) {
			state.alertList.data = state.alertList.data.map((alert) => {
				if (alert.uuid !== payload.uuid) { return alert }
				return { ...alert,
					...payload
				}
			})
		},
		[ RESTART_ALERT ] (state) {
			state.alertDetails.data = { ...newAlert }
		},
		[ UPDATE_ALERT_QUERY ] (state, query) {
			/*
				Create new alert with given query to current alert, for creating the next alert with it.
				Clicking on new alert, or edit of existing will override it.
			 */
			state.alertDetails.data = { ...newAlert,
				query: query
			}
		}
	},
	actions: {
		[ FETCH_ALERTS ] ({dispatch}, payload) {
			/*
				Call to api for getting all alerts, according to skip, limit and filter
				The mutation UPDATE_ALERTS is called with the returned controls or error, to fill it in the state
			*/
			if (!payload.skip) {
				payload.skip = 0
			}
			let param = `?limit=${payload.limit}&skip=${payload.skip}`
			if (payload.filter && Object.keys(payload.filter).length) {
				param += `&filter=${JSON.stringify(payload.filter)}`
			}
			return dispatch(REQUEST_API, {
				rule: `reports${param}`,
				type: UPDATE_ALERTS,
				payload: {
					restart: payload.skip === 0
				}
			})
		},
		[ ARCHIVE_ALERT ] ({dispatch, commit}, alertId) {
			/*
				Call to api to add \ update field 'archived' with true, so that this alert will be ignored
				If completed successfully, matching row is removed from alertsList (instead of re-fetching),
				using a call to the mutation REMOVE_ALERT
			 */
			if (!alertId) { return }
			dispatch(REQUEST_API, {
				rule: `reports/${alertId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response.data !== '') {
					return
				}
				commit(REMOVE_ALERT, alertId)
			})
		},
		[ UPDATE_ALERT ] ({dispatch}, payload) {
			/*
				Call to api to add \ update an alert. If given an id, the matching alert will be updated with the
				new controls. Otherwise a new alert will be added to the collection.
				If completed successfully, id of added \ updated alert should be returned and together with the
				controls, they are added to the alertList (instead of re-fetching), using a call to the mutation ADD_ALERT
			 */
			if (!payload || !payload.id) { return }
			let rule = 'reports'
			let method = 'PUT'
			if (payload.id !== 'new') {
				rule += '/' + payload.id
				method = 'POST'
			}
			dispatch(REQUEST_API, {
				rule: rule,
				method: method,
				data: payload
			}).then(() => {
				dispatch(FETCH_ALERTS, {skip: 0, limit: 50})
			})
		}
	}
}