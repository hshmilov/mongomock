import { REQUEST_API } from '../actions'

export const FETCH_LIFECYCLE = 'FETCH_LIFECYCLE'
export const UPDATE_LIFECYCLE = 'UPDATE_LIFECYCLE'

export const FETCH_DISCOVERY_DATA = 'FETCH_DISCOVERY_DATA'
export const UPDATE_DISCOVERY_DATA = 'UPDATE_DISCOVERY_DATA'

export const FETCH_DASHBOARD = 'FETCH_DASHBOARD'
export const UPDATE_DASHBOARD = 'UPDATE_DASHBOARD'
export const SAVE_DASHBOARD = 'SAVE_DASHBOARD'

export const REMOVE_DASHBOARD = 'REMOVE_DASHBOARD'
export const UPDATE_REMOVED_DASHBOARD = 'UPDATE_REMOVED_DASHBOARD'

export const FETCH_DASHBOARD_COVERAGE = 'FETCH_DASHBOARD_COVERAGE'
export const UPDATE_DASHBOARD_COVERAGE = 'UPDATE_DASHBOARD_COVERAGE'

export const FETCH_HISTORICAL_SAVED_CARD = 'FETCH_HISTORICAL_SAVED_CARD'

export const FETCH_DASHBOARD_FIRST_USE = 'FETCH_DASHBOARD_FIRST_USE'
export const UPDATE_DASHBOARD_FIRST_USE = 'UPDATE_DASHBOARD_FIRST_USE'

export const dashboard = {
	state: {
		lifecycle: { data: {}, fetching: false, error: '' },
		dataDiscovery: {
			devices: {data: {}, fetching: false, error: ''},
			users: {data: {}, fetching: false, error: '' }
		},
		charts: { data: [], fetching: false, error: '' },
		coverage: { data: {}, fetching: false, error: '' },
		firstUse: { data: null, fetching: false, error: '' }
	},
	mutations: {
		[ UPDATE_LIFECYCLE ] (state, payload) {
			state.lifecycle.fetching = payload.fetching
			state.lifecycle.error = payload.error
			if (payload.data && payload.data.sub_phases) {
				state.lifecycle.data = {
					subPhases: payload.data.sub_phases,
					nextRunTime: payload.data.next_run_time,
					status: payload.data.status
				}
			}
		},
		[ UPDATE_DISCOVERY_DATA] (state, payload) {
			if (!payload || !payload.module || !state.dataDiscovery[payload.module]) return
			state.dataDiscovery[payload.module].fetching = payload.fetching
			state.dataDiscovery[payload.module].error = payload.error
			if (payload.data && Object.keys(payload.data).length) {
				state.dataDiscovery[payload.module].data = { ...payload.data }
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
			state.charts.data = state.charts.data.filter(dashboard => dashboard.uuid !== dashboardId)
		},
		[ UPDATE_DASHBOARD_FIRST_USE] (state, payload) {
            state.firstUse.fetching = payload.fetching
            state.firstUse.error = payload.error
			if (payload.data !== undefined) {
				state.firstUse.data = payload.data
			}
		}
	},
	actions: {
		[ FETCH_LIFECYCLE ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/lifecycle',
				type: UPDATE_LIFECYCLE
			})
		},
		[ FETCH_DISCOVERY_DATA ] ({ dispatch, state }, payload) {
			if (!payload || !payload.module || !state.dataDiscovery[payload.module]) return
			return dispatch(REQUEST_API, {
				rule: `dashboard/adapter_data/${payload.module}`,
				type: UPDATE_DISCOVERY_DATA,
				payload
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
				rule: `saved_card_results/${encodeURI(payload.cardUuid)}?date_to=${encodeURI(payload.date)} 23:59:59&date_from=${encodeURI(payload.date)}`,
			})
		},
		[ FETCH_DASHBOARD_FIRST_USE ] ({ dispatch }) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/first_use',
				type: UPDATE_DASHBOARD_FIRST_USE
			})
		}
	}
}