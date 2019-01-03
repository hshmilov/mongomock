import { REQUEST_API } from '../actions'
import { FETCH_DATA_CONTENT } from '../actions'

export const FETCH_ALERTS = 'FETCH_ALERTS'
export const UPDATE_ALERTS = 'UPDATE_ALERTS'
export const SET_ALERT = 'SET_ALERT'
export const ARCHIVE_ALERTS = 'ARCHIVE_ALERTS'
export const REMOVE_ALERTS = 'REMOVE_ALERTS'
export const UPDATE_ALERT = 'UPDATE_ALERT'
export const SAVE_ALERT = 'SAVE_ALERT'
export const UPDATE_ALERT_VIEW = 'UPDATE_ALERT_VIEW'


const newAlert = {
	id: 'new',
	name: '',
	triggers: {
         every_discovery: false,
         new_entities: false,
         previous_entities: false,
         above: 0,
         below: 0,
    },
	actions: [],
	view: '',
	viewEntity: '',
	retrigger: true,
	triggered: false,
	severity: 'info',
    period: 'all'
}

export const alert = {
	state: {
		/* Alerts DataTable State */
		content: { data: [], fetching: false, error: ''},
		count: { data: 0, fetching: false, error: ''},
		view: {
			page: 0, pageSize: 20, fields: [
				'name', 'report_creation_time', 'triggered', 'view', 'severity'
			], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
		},
		fields: {
			data: {
				generic: [
					{ name: 'name', title: 'Name', type: 'string' },
					{ name: 'report_creation_time', title: 'Creation Time', type: 'string', format: 'date-time' },
					{ name: 'triggered', title: 'Times Triggered', type: 'integer' },
					{ name: 'view', title: 'Query Name', type: 'string'},
					{ name: 'severity', title: 'Severity', type: 'string', format: 'icon' }
				]
			}
		},

		/* Data of alerts currently being configured */
		current: { fetching: false, data: { ...newAlert }, error: '' }
	},
	mutations: {
		[ UPDATE_ALERTS ] (state, payload) {
			/*
				Called once before AJAX call is made, just to update that fetching has started.
				Called again either with error, if call threw an error or with response, if was returned from call.
				The controls is expected to be a list of alerts to be added to current list
				(called for each page, until all controls is collected)
				If there is need to re-fetch, list should be restarted first
			 */
			state.content.fetching = payload.fetching
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
				state.content.data = payload.restart? processedData : [ ...state.content.data, ...processedData ]
			}
			if (payload.error) {
				state.content.error = payload.error
			}
		},
		[ SET_ALERT ] (state, alertId) {
			/*
				The controls is expected to be fields and values of a specific alerts and is stored for use in the
				alerts configuration page
			 */
			if (!alertId) return
			let found = false
			state.content.data.forEach((alert) => {
				if (alert.uuid === alertId) {
					state.current.data = alert
					found = true
				}
			})
			if (!found) state.current.data = { ...newAlert }
		},
		[ REMOVE_ALERTS ] (state, selection) {
			/*
				Filter current list of queries so it no longer has an object by the id of given payload
			 */
			state.content.data = [ ...state.content.data ].filter(function(alert) {
				if (selection.include) {
					return !selection.ids.includes(alert.uuid)
				} else {
					return selection.ids.includes(alert.uuid)
				}
			})
			state.count.data = state.content.data.length
		},
		[ SAVE_ALERT ] (state, payload) {
			state.content.data = state.content.data.map((alert) => {
				if (alert.uuid !== payload.uuid) { return alert }
				return { ...alert,
					...payload
				}
			})
		},
		[ UPDATE_ALERT_VIEW ] (state, view) {
			/*
				Create new alerts with given query to current alerts, for creating the next alerts with it.
				Clicking on new alerts, or edit of existing will override it.
			 */
			state.current.data = { ...newAlert,
				view: view
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
				rule: `alert${param}`,
				type: UPDATE_ALERTS,
				payload: {
					restart: payload.skip === 0
				}
			})
		},
		[ ARCHIVE_ALERTS ] ({dispatch, commit}, selection) {
			/*
				Call to api to add \ update field 'archived' with true, so that this alerts will be ignored
				If completed successfully, matching row is removed from alertsList (instead of re-fetching),
				using a call to the mutation REMOVE_ALERT
			 */
			if (!selection || (!selection.include && !selection.ids)) return
			dispatch(REQUEST_API, {
				rule: 'alert',
				method: 'DELETE',
				data: selection
			}).then((response) => {
				if (response.data !== '') {
					return
				}
				commit(REMOVE_ALERTS, selection)
			})
		},
		[ UPDATE_ALERT ] ({dispatch}, payload) {
			/*
				Call to api to add \ update an alerts. If given an id, the matching alerts will be updated with the
				new controls. Otherwise a new alerts will be added to the collection.
				If completed successfully, id of added \ updated alerts should be returned and together with the
				controls, they are added to the content (instead of re-fetching), using a call to the mutation ADD_ALERT
			 */
			if (!payload || !payload.id) { return }
			let rule = 'alert'
			let method = 'PUT'
			if (payload.id !== 'new') {
				rule += '/' + payload.id
				method = 'POST'
			}
			return dispatch(REQUEST_API, {
				rule: rule,
				method: method,
				data: payload
			}).then(() => dispatch(FETCH_DATA_CONTENT, { module: 'alert', skip: 0, limit: 20 }))
		}
	}
}
