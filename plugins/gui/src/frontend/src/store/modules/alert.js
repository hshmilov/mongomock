import { REQUEST_API } from '../actions'

export const FETCH_ALERTS = 'FETCH_ALERTS'
export const UPDATE_ALERTS = 'UPDATE_ALERTS'
export const FETCH_ALERT = 'FETCH_ALERT'
export const SET_ALERT = 'SET_ALERT'
export const ARCHIVE_ALERT = 'ARCHIVE_ALERT'
export const REMOVE_ALERT = 'REMOVE_ALERT'
export const RESTART_ALERTS = 'RESTART_ALERTS'
export const RESTART_ALERT = 'RESTART_ALERT'
export const UPDATE_ALERT = 'UPDATE_ALERT'
export const ADD_ALERT = 'ADD_ALERT'
export const UPDATE_ALERT_QUERY = 'UPDATE_ALERT_QUERY'

const newAlert = {
	id: 'new',
	name: '',
	criteria: undefined,
	query: '',
	notification: false,
	retrigger: true,
	severity: 'error',
	triggered: false
}

export const alert = {
	state: {
		/* All alerts */
		alertList: {fetching: false, data: [], error: ''},
		/* Statically defined fields that should be presented for each alert, in this order */
		fields: [
			{ path: 'severity', name: 'Severity', default: true, type: 'status' },
			{ path: 'name', name: 'Name', default: true, control: 'text'},
			{ path: 'timestamp', name: 'Creation Time', type: 'timestamp', default: true, control: 'text' },
			{ path: 'type', name: 'Source', default: true, type: 'type' },
			{ path: 'message', name: 'Alert Info', default: true }
		],
		/* Data of alert currently being configured */
		currentAlert: { fetching: false, data: { ...newAlert }, error: '' }
	},
	getters: {
		filterFields(state) {
			return state.fields.filter((field) => {
				return field.control !== undefined
			})
		}
	},
	mutations: {
		[ UPDATE_ALERTS ] (state, payload) {
			/*
				Called once before AJAX call is made, just to update that fetching has started.
				Called again either with error, if call threw an error or with response, if was returned from call.
				The data is expected to be a list of alerts to be added to current list
				(called for each page, until all data is collected)
				If there is need to re-fetch, list should be restarted first
			 */
			state.alertList.fetching = payload.fetching
			if (payload.data) {
				let processedData = []
				payload.data.forEach(function(alert) {
					let message = 'No change detected'
					if (alert.triggered) {
						/* Condition was met - updating to informative message, according to criteria */
						switch (alert.criteria) {
							case 0:
								message = 'Change'
								break
							case 1:
								message = 'Increase'
								break
							case -1:
								message = 'Decrease'
								break
						}
						message += ' detected in query result'
					}
					processedData.push({ ...alert,
						severity: 'error',
						type: 'User defined by: Administrator',
						message: message
					})
				})
				state.alertList.data = [ ...state.alertList.data, ...processedData ]
			}
			if (payload.error) {
				state.alertList.error = payload.error
			}
		},
		[ SET_ALERT ] (state, payload) {
			/*
				The data is expected to be fields and values of a specific alert and is stored for use in the
				alert configuration page
			 */
			state.currentAlert.fetching = payload.fetching
			if (payload.data) {
				state.currentAlert.data = { ...payload.data,
					query: payload.data.query.replace(/\\/g, '')
				}
			}
			if (payload.error) {
				state.currentAlert.error = payload.error
			}
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
		[ RESTART_ALERT ] (state) {
			state.currentAlert.data = { ...newAlert }
		},
		[ UPDATE_ALERT_QUERY ] (state, query) {
			/*
				Create new alert with given query to current alert, for creating the next alert with it.
				Clicking on new alert, or edit of existing will override it.
			 */
			state.currentAlert.data = { ...newAlert,
				query: query
			}
		}
	},
	actions: {
		[ FETCH_ALERTS ] ({dispatch}, payload) {
			/*
				Call to api for getting all alerts, according to skip, limit and filter
				The mutation UPDATE_ALERTS is called with the returned data or error, to fill it in the state
			*/
			if (!payload.skip) { payload.skip = 0 }
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
			/*
				Call to api for getting a single alert, in order to present in alert config page
				The mutation UPDATE_ALERT is called with the returned data or error, to fill it in the state
			*/
			if (!alertId) { return }
			dispatch(REQUEST_API, {
				rule: `api/alerts/${alertId}`,
				type: SET_ALERT
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
				rule: `api/alerts/${alertId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response !== '') {
					return
				}
				commit(REMOVE_ALERT, alertId)
			})
		},
		[ UPDATE_ALERT ] ({dispatch, commit}, payload) {
			/*
				Call to api to add \ update an alert. If given an id, the matching alert will be updated with the
				new data. Otherwise a new alert will be added to the collection.
				If completed successfully, id of added \ updated alert should be returned and together with the
				data, they are added to the alertList (instead of re-fetching), using a call to the mutation ADD_ALERT
			 */
			if (!payload || !payload.id) { return }
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