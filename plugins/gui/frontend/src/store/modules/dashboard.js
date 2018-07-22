import { REQUEST_API } from '../actions'

export const FETCH_LIFECYCLE = 'FETCH_LIFECYCLE'
export const UPDATE_LIFECYCLE = 'UPDATE_LIFECYCLE'

export const UPDATE_LIFECYCLE_RATE = 'UPDATE_LIFECYCLE_RATE'

export const FETCH_ADAPTER_DEVICES = 'FETCH_ADAPTER_DEVICES'
export const UPDATE_ADAPTER_DEVICES = 'UPDATE_ADAPTER_DEVICES'

export const FETCH_DASHBOARD = 'FETCH_DASHBOARD'
export const UPDATE_DASHBOARD = 'UPDATE_DASHBOARD'
export const SAVE_DASHBOARD = 'SAVE_DASHBOARD'

export const REMOVE_DASHBOARD = 'REMOVE_DASHBOARD'
export const UPDATE_REMOVED_DASHBOARD = 'UPDATE_REMOVED_DASHBOARD'

export const FETCH_DASHBOARD_COVERAGE = 'FETCH_DASHBOARD_COVERAGE'
export const UPDATE_DASHBOARD_COVERAGE = 'UPDATE_DASHBOARD_COVERAGE'

export const FETCH_HISTORICAL_SAVED_CARD = 'FETCH_HISTORICAL_SAVED_CARD'
export const FETCH_HISTORICAL_SAVED_CARD_MIN = 'FETCH_HISTORICAL_SAVED_CARD_MIN'

export const dashboard = {
	state: {
		lifecycle: { data: {}, fetching: false, error: '' },
		adapterDevices: { data: {}, fetching: false, error: '' },
		charts: { data: [], fetching: false, error: ''},
		coverage: { data: {}, fetching: false, error: ''}
	},
	mutations: {
		[ UPDATE_LIFECYCLE ] (state, payload) {
			state.lifecycle.fetching = payload.fetching
			state.lifecycle.error = payload.error
			if (payload.data && payload.data.sub_phases) {
				state.lifecycle.data = {
					subPhases: payload.data.sub_phases,
					nextRunTime: payload.data.next_run_time
				}
			}
		},
		[ UPDATE_ADAPTER_DEVICES] (state, payload) {
			state.adapterDevices.fetching = payload.fetching
			state.adapterDevices.error = payload.error
			if (payload.data && Object.keys(payload.data).length) {
				state.adapterDevices.data = { ...payload.data }
			}
		},
		[ UPDATE_DASHBOARD ] (state, payload) {
			state.charts.fetching = payload.fetching
			state.charts.error = payload.error
			if (payload.data) {
				state.charts.data = payload.data
			}
		},
		[ UPDATE_DASHBOARD_COVERAGE ] (state, payload) {
			state.coverage.fetching = payload.fetching
			state.coverage.error = payload.error
			if (payload.data && Object.keys(payload.data).length) {
				state.coverage.data = payload.data
			}
		},
		[ UPDATE_REMOVED_DASHBOARD ] (state, dashboardId) {
			state.charts.data = state.charts.data.filter(dashboard => dashboard.uuid != dashboardId)
		}
	},
	actions: {
		[ FETCH_LIFECYCLE ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/lifecycle',
				type: UPDATE_LIFECYCLE
			})
		},
        [ UPDATE_LIFECYCLE_RATE ] ({dispatch}) {
            return dispatch(REQUEST_API, {
                rule: 'dashboard/lifecycle',
                type: UPDATE_LIFECYCLE,
                method: 'POST'
            })
        },
		[ FETCH_ADAPTER_DEVICES ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/adapter_devices',
				type: UPDATE_ADAPTER_DEVICES
			})
		},
		[ FETCH_DASHBOARD ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard',
				type: UPDATE_DASHBOARD
			})
		},
		[ SAVE_DASHBOARD ] ({dispatch}, payload) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard',
				method: 'POST',
				data: payload
			}).then((response) => {
				if (response.status === 200 && response.data) {
					dispatch(FETCH_DASHBOARD)
				}
			})
		},
		[ REMOVE_DASHBOARD ] ({dispatch, commit}, dashboardId) {
			if (!dashboardId) return
			return dispatch(REQUEST_API, {
				rule: `dashboard/${dashboardId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response.status === 200) {
					commit(UPDATE_REMOVED_DASHBOARD, dashboardId)
				}
			})
		},
		[ FETCH_DASHBOARD_COVERAGE ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/coverage',
				type: UPDATE_DASHBOARD_COVERAGE
			})
		},
		[ FETCH_HISTORICAL_SAVED_CARD ] ({ dispatch }, payload) {
			return dispatch(REQUEST_API, {
				rule: `saved_card_results/${encodeURI(payload.cardName)}?date_to=${encodeURI(payload.date)} 23:59:59&date_from=${encodeURI(payload.date)}`,
			})
		},
		[ FETCH_HISTORICAL_SAVED_CARD_MIN ] ({ dispatch }, payload) {
			return dispatch(REQUEST_API, {
				rule: `saved_card_results/${encodeURIComponent(payload.cardName)}/min`
			})
		}
	}
}