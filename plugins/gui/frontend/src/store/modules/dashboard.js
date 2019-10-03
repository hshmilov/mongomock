import { REQUEST_API, downloadFile } from '../actions'

export const FETCH_LIFECYCLE = 'FETCH_LIFECYCLE'
export const UPDATE_LIFECYCLE = 'UPDATE_LIFECYCLE'

export const FETCH_DISCOVERY_DATA = 'FETCH_DISCOVERY_DATA'
export const UPDATE_DISCOVERY_DATA = 'UPDATE_DISCOVERY_DATA'

export const FETCH_DASHBOARD_SPACES = 'FETCH_DASHBOARD_SPACES'
export const UPDATE_DASHBOARD_SPACES = 'UPDATE_DASHBOARD_SPACES'
export const FETCH_DASHBOARD_PANELS = 'FETCH_DASHBOARD_PANELS'
export const UPDATE_DASHBOARD_PANELS = 'UPDATE_DASHBOARD_PANELS'
export const FETCH_DASHBOARD_PANEL = 'FETCH_DASHBOARD_PANEL'
export const UPDATE_DASHBOARD_PANEL = 'UPDATE_DASHBOARD_PANEL'

export const SAVE_DASHBOARD_SPACE = 'SAVE_DASHBOARD_SPACE'
export const UPDATE_ADDED_SPACE = 'UPDATE_ADDED_SPACE'
export const CHANGE_DASHBOARD_SPACE = 'CHANGE_DASHBOARD_SPACE'
export const UPDATE_CHANGED_SPACE = 'UPDATE_CHANGED_SPACE'
export const REMOVE_DASHBOARD_SPACE = 'REMOVE_DASHBOARD_SPACE'
export const UPDATE_REMOVED_SPACE = 'UPDATE_REMOVED_SPACE'

export const SAVE_DASHBOARD_PANEL = 'SAVE_DASHBOARD_PANEL'
export const CHANGE_DASHBOARD_PANEL = 'CHANGE_DASHBOARD_PANEL'
export const REMOVE_DASHBOARD_PANEL = 'REMOVE_DASHBOARD_PANEL'
export const UPDATE_REMOVED_PANEL = 'UPDATE_REMOVED_PANEL'
export const ADD_NEW_PANEL = 'ADD_NEW_PANEL'
export const UPDATE_CHANGED_PANEL = 'UPDATE_CHANGED_PANEL'

export const FETCH_HISTORICAL_SAVED_CARD = 'FETCH_HISTORICAL_SAVED_CARD'

export const FETCH_DASHBOARD_FIRST_USE = 'FETCH_DASHBOARD_FIRST_USE'
export const UPDATE_DASHBOARD_FIRST_USE = 'UPDATE_DASHBOARD_FIRST_USE'
export const FETCH_CHART_SEGMENTS_CSV = 'FETCH_CHART_SEGMENTS_CSV'

export const SET_CURRENT_SPACE = 'SET_CURRENT_SPACE'

export const dashboard = {
	state: {
		lifecycle: { data: {}, fetching: false, error: '' },
		dataDiscovery: {
			devices: { data: {}, fetching: false, error: '' },
			users: { data: {}, fetching: false, error: '' }
		},
		spaces: { data: [], fetching: false, error: '' },
		panels: { data: [], fetching: false, error: '' },
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
					status: payload.data.status,
					lastStartTime: payload.data.last_start_time,
					lastFinishedTime: payload.data.last_finished_time
				}
			}
		},
		[UPDATE_DISCOVERY_DATA](state, payload) {
			if (!payload || !payload.module || !state.dataDiscovery[payload.module]) return
			state.dataDiscovery[payload.module].fetching = payload.fetching
			state.dataDiscovery[payload.module].error = payload.error
			if (payload.data && Object.keys(payload.data).length) {
				state.dataDiscovery[payload.module].data = { ...payload.data }
			}
		},
		[UPDATE_DASHBOARD_SPACES](state, payload) {
			state.spaces.fetching = payload.fetching
			state.spaces.error = payload.error
			if (!payload.data) {
				return
			}
			state.spaces.data = payload.data.spaces
			if(state.panels.data && state.panels.data.length > 0) {
				let currentPanels = {}
				state.panels.data.forEach(panel => {
					currentPanels[panel.uuid] = panel
				})
				payload.data.panels.forEach(panel => {
					if(!currentPanels[panel.uuid]){
						state.panels.data.push(panel)
					}
				})
			} else {
				state.panels.data = payload.data.panels
			}
		},
		[UPDATE_DASHBOARD_PANELS](state, payload) {
			state.panels.fetching = payload.fetching
			state.panels.error = payload.error
			if (!payload.data) {
				return
			}
			if (!state.panels.data.length) {
				state.panels.data = payload.data
			} else {
				payload.data.forEach((item, index) => {
					let dataTail = item['data_tail']
					if (payload.skip + index < state.panels.data.length) {
						let oldItem = state.panels.data[payload.skip + index]
						if (!oldItem.data.length) {
							if (dataTail && dataTail.length) {
								item.data[item.count - 1] = null
								item.data.splice(item.count - dataTail.length, dataTail.length, ...dataTail)
							}
							state.panels.data[payload.skip + index] = item
						} else {
							oldItem.data.splice(0, item.data.length, ...item.data)
							if (dataTail && dataTail.length) {
								if (item.count > oldItem.data.length) {
									oldItem.data[item.count - 1] = null
								}
								oldItem.data.splice(item.count - dataTail.length, dataTail.length, ...dataTail)
							}
						}
					} else {
						if (dataTail && dataTail.length) {
							item.data[item.count - 1] = null
							item.data.splice(item.count - dataTail.length, dataTail.length, ...dataTail)
						}
						state.panels.data.push(item)
					}
				})
				state.panels.data = [...state.panels.data]
			}
		},
        [ADD_NEW_PANEL](state, payload) {
            let newPanel = {
                uuid: payload.panel_id,
                name: payload.name,
                space: payload.space,
                data: [],
                loading: true
            }
            state.panels.data.push(newPanel)
        },
		[UPDATE_DASHBOARD_PANEL](state, payload) {
			if (!payload.data) {
				return
			}
			let panel = state.panels.data.find(panel => panel.uuid === payload.uuid)
			if (!panel) {
				return
			}
			if (!payload.data.length) {
				panel.data = []
				panel.loading = payload.loading
			} else {
				panel.data.splice(payload.skip, payload.data.length, ...payload.data)
				panel.loading = false
			}
		},
		[UPDATE_ADDED_SPACE](state, payload) {
			state.spaces.data.push(payload)
		},
		[UPDATE_CHANGED_SPACE](state, payload) {
			state.spaces.data = state.spaces.data.map(space => {
				if (space.uuid !== payload.id) return space

				return { ...space, name: payload.name }
			})
		},
		[UPDATE_REMOVED_SPACE](state, spaceId) {
			state.spaces.data = state.spaces.data.filter(space => space.uuid !== spaceId)
		},
		[UPDATE_REMOVED_PANEL](state, dashboardId) {
			state.panels.data = state.panels.data.filter(panel => panel.uuid !== dashboardId)
		},
		[UPDATE_DASHBOARD_FIRST_USE](state, payload) {
			state.firstUse.fetching = payload.fetching
			state.firstUse.error = payload.error
			if (payload.data !== undefined) {
				state.firstUse.data = payload.data
			}
		},
		[SET_CURRENT_SPACE](state, spaceId) {
			state.currentSpace = spaceId
		}
	},
	actions: {
		[FETCH_LIFECYCLE]({ dispatch }) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/lifecycle',
				type: UPDATE_LIFECYCLE
			})
		},
		[FETCH_DISCOVERY_DATA]({ dispatch, state }, payload) {
			if (!payload || !payload.module || !state.dataDiscovery[payload.module]) return
			return dispatch(REQUEST_API, {
				rule: `dashboard/adapter_data/${payload.module}`,
				type: UPDATE_DISCOVERY_DATA,
				payload
			})
		},
		[FETCH_DASHBOARD_SPACES]({ dispatch }, payload) {
			return dispatch(REQUEST_API, {
				rule: 'dashboards',
				type: UPDATE_DASHBOARD_SPACES,
				payload
			})
		},
		[FETCH_DASHBOARD_PANELS]({ dispatch }, payload) {
			if (!payload) {
				payload = {}
			}
			if (!payload.skip) {
				payload.skip = 0
			}
			if (!payload.limit) {
				payload.limit = 2
			}
			return dispatch(REQUEST_API, {
				rule: `dashboards/panels?skip=${payload.skip}&limit=${payload.limit}`,
				type: UPDATE_DASHBOARD_PANELS,
				payload
			}).then(response => {
				if (response.data && response.data.length === payload.limit) {
					dispatch(FETCH_DASHBOARD_PANELS, {
						...payload,
						skip: payload.skip + payload.limit
					})
				}
			})
		},
		[FETCH_DASHBOARD_PANEL]({ dispatch, commit }, payload) {
			return dispatch(REQUEST_API, {
				rule: `dashboards/panels/${payload.uuid}?skip=${payload.skip}&limit=${payload.limit}`,
				type: UPDATE_DASHBOARD_PANEL,
				payload
			})
		},
		[SAVE_DASHBOARD_SPACE]({ dispatch, commit }, name) {
			return dispatch(REQUEST_API, {
				rule: 'dashboards',
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
		[CHANGE_DASHBOARD_SPACE]({ dispatch, commit }, payload) {
			return dispatch(REQUEST_API, {
				rule: `dashboards/${payload.id}`,
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
		[REMOVE_DASHBOARD_SPACE]({ dispatch, commit }, spaceId) {
			return dispatch(REQUEST_API, {
				rule: `dashboards/${spaceId}`,
				method: 'DELETE'
			}).then(response => {
				if (response.status === 200) {
					commit(UPDATE_REMOVED_SPACE, spaceId)
				}
			})
		},
		[SAVE_DASHBOARD_PANEL]({ dispatch, commit }, payload) {
			return dispatch(REQUEST_API, {
				rule: `dashboards/${payload.space}/panels`,
				method: 'POST',
				data: payload.data
			}).then(response => {
				if (response.status === 200 && response.data) {
					commit(ADD_NEW_PANEL, {
						space: payload.space,
						panel_id: response.data,
						name: payload.data.name,
						data: []
					})
					dispatch(FETCH_DASHBOARD_PANELS)
				}
				return response
			})
		},
		[CHANGE_DASHBOARD_PANEL]({ dispatch, commit }, payload) {
			return dispatch(REQUEST_API, {
				rule: `dashboards/panels/${payload.uuid}`,
				method: 'POST',
				data: payload.data
			}).then(response => {
				if (response.status === 200) {
					commit(UPDATE_DASHBOARD_PANEL, {
						uuid: payload.uuid,
						skip: 0,
						data: [],
                        loading: true
					})
					dispatch(FETCH_DASHBOARD_PANELS)
				}
				return response
			})
		},
		[REMOVE_DASHBOARD_PANEL]({ dispatch, commit }, panelId) {
			if (!panelId) return
			return dispatch(REQUEST_API, {
				rule: `dashboards/panels/${panelId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response.status === 200) {
					commit(UPDATE_REMOVED_PANEL, panelId)
				}
			})
		},
		[FETCH_HISTORICAL_SAVED_CARD]({ dispatch }, { cardId, date }) {
			return dispatch(REQUEST_API, {
				rule: `saved_card_results/${encodeURI(cardId)}?date_to=${encodeURI(date)} 23:59:59&date_from=${encodeURI(date)}`
			})
		},
		[FETCH_DASHBOARD_FIRST_USE]({ dispatch }) {
			return dispatch(REQUEST_API, {
				rule: 'dashboard/first_use',
				type: UPDATE_DASHBOARD_FIRST_USE
			})
		},
		[FETCH_CHART_SEGMENTS_CSV]({ state, dispatch }, { panelId, chartName }) {
			return dispatch(REQUEST_API, {
				rule: `dashboards/panels/${panelId}/csv`,
			}).then((response) => {
				downloadFile('csv', response, chartName)
			})
		}
	}
}
