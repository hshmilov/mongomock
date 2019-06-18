import { REQUEST_API } from '../actions'

export const FETCH_LIFECYCLE = 'FETCH_LIFECYCLE'
export const UPDATE_LIFECYCLE = 'UPDATE_LIFECYCLE'

export const FETCH_DISCOVERY_DATA = 'FETCH_DISCOVERY_DATA'
export const UPDATE_DISCOVERY_DATA = 'UPDATE_DISCOVERY_DATA'

export const FETCH_DASHBOARD_SPACES = 'FETCH_DASHBOARD_SPACES'
export const UPDATE_DASHBOARD_SPACES = 'UPDATE_DASHBOARD_SPACES'
export const SAVE_DASHBOARD_SPACE = 'SAVE_DASHBOARD_SPACE'
export const UPDATE_ADDED_SPACE = 'UPDATE_ADDED_SPACE'
export const CHANGE_DASHBOARD_SPACE = 'CHANGE_DASHBOARD_SPACE'
export const UPDATE_CHANGED_SPACE = 'UPDATE_CHANGED_SPACE'
export const REMOVE_DASHBOARD_SPACE = 'REMOVE_DASHBOARD_SPACE'
export const UPDATE_REMOVED_SPACE = 'UPDATE_REMOVED_SPACE'

export const SAVE_DASHBOARD_PANEL = 'SAVE_DASHBOARD_PANEL'
export const REMOVE_DASHBOARD_PANEL = 'REMOVE_DASHBOARD_PANEL'
export const UPDATE_REMOVED_PANEL = 'UPDATE_REMOVED_PANEL'

export const FETCH_HISTORICAL_SAVED_CARD = 'FETCH_HISTORICAL_SAVED_CARD'

export const FETCH_DASHBOARD_FIRST_USE = 'FETCH_DASHBOARD_FIRST_USE'
export const UPDATE_DASHBOARD_FIRST_USE = 'UPDATE_DASHBOARD_FIRST_USE'

export const SET_CURRENT_SPACE = 'SET_CURRENT_SPACE'

export const dashboard = {
	state: {
		lifecycle: { data: {}, fetching: false, error: '' },
		dataDiscovery: {
			devices: {data: {}, fetching: false, error: ''},
			users: {data: {}, fetching: false, error: '' }
		},
		spaces: { data: [], fetching: false, error: '' },
		currentSpace: '',
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
		[ UPDATE_DASHBOARD_SPACES ] (state, payload) {
			state.spaces.fetching = payload.fetching
			state.spaces.error = payload.error
			if (!payload.data) {
					return
			}
			state.spaces.data = payload.data
		},
		[ UPDATE_ADDED_SPACE ] (state, payload) {
			state.spaces.data.push(payload)
		},
		[ UPDATE_CHANGED_SPACE ] (state, payload) {
			state.spaces.data = state.spaces.data.map(space => {
				if (space.uuid !== payload.id) return space

				return {...space, name: payload.name}
			})
		},
		[ UPDATE_REMOVED_SPACE ] (state, spaceId) {
			state.spaces.data = state.spaces.data.filter(space => space.uuid !== spaceId)
		},
		[ UPDATE_REMOVED_PANEL ] (state, dashboardId) {
			state.spaces.data = state.spaces.data.map(space => {
				return {
					...space,
					panels: space.panels.filter(dashboard => dashboard.uuid !== dashboardId)
				}
			})
		},
		[ UPDATE_DASHBOARD_FIRST_USE] (state, payload) {
            state.firstUse.fetching = payload.fetching
            state.firstUse.error = payload.error
			if (payload.data !== undefined) {
				state.firstUse.data = payload.data
			}
		}, [ SET_CURRENT_SPACE ] (state, spaceId) {
			state.currentSpace = spaceId
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
		[ FETCH_DASHBOARD_SPACES ] ({dispatch}, payload) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/spaces',
				type: UPDATE_DASHBOARD_SPACES,
				payload
			})
		},
		[ SAVE_DASHBOARD_SPACE ] ({dispatch, commit}, name) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/spaces',
				method: 'POST',
				data: {
					name
				}
			}).then(response => {
				if (response.status === 200 && response.data) {
					commit(UPDATE_ADDED_SPACE, {
						uuid: response.data, name,
						type: 'custom', panels: []
					})
				}
				return response.data
			})
		},
		[ CHANGE_DASHBOARD_SPACE ] ({dispatch, commit}, payload) {
			return dispatch(REQUEST_API, {
				rule: `dashboard/spaces/${payload.id}`,
				method: 'PUT',
				data: {
					name: payload.name
				}
			}).then(response => {
				if (response.status === 200) {
					commit(UPDATE_CHANGED_SPACE, payload)
				}
			})
		},
		[ REMOVE_DASHBOARD_SPACE ] ({dispatch, commit}, spaceId) {
			return dispatch(REQUEST_API, {
				rule: `dashboard/spaces/${spaceId}`,
				method: 'DELETE'
			}).then(response => {
				if (response.status === 200) {
					commit(UPDATE_REMOVED_SPACE, spaceId)
				}
			})
		},
		[ SAVE_DASHBOARD_PANEL ] ({dispatch}, payload) {
			return dispatch(REQUEST_API, {
				rule: `dashboard/spaces/${payload.space}/panels`,
				method: 'POST',
				data: payload.data
			}).then(response => {
				if (response.status === 200 && response.data) {
					dispatch(FETCH_DASHBOARD_SPACES)
				}
				return response
			})
		},
		[ REMOVE_DASHBOARD_PANEL ] ({dispatch, commit}, panelId) {
			if (!panelId) return
			return dispatch(REQUEST_API, {
				rule: `dashboard/panels/${panelId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response.status === 200) {
					commit(UPDATE_REMOVED_PANEL, panelId)
				}
			})
		},
		[ FETCH_HISTORICAL_SAVED_CARD ] ({ dispatch }, {cardId, date}) {
			return dispatch(REQUEST_API, {
				rule: `saved_card_results/${encodeURI(cardId)}?date_to=${encodeURI(date)} 23:59:59&date_from=${encodeURI(date)}`
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
