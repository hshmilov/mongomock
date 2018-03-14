import { REQUEST_API } from '../actions'

export const UPDATE_REFRESH_RATE = 'UPDATE_REFRESH_RATE'
export const UPDATE_SINGLE_ADAPTER = 'UPDATE_SINGLE_ADAPTER'
export const UPDATE_MULTI_LINE = 'UPDATE_MULTI_LINE'
export const FETCH_SETTINGS = 'FETCH_SETTINGS'
export const UPDATE_SETTINGS = 'UPDATE_SETTINGS'
export const SAVE_SETTINGS = 'SAVE_SETTINGS'


export const settings = {
	state: {
		fetching: false, error: '', data: {
			refreshRate: 30,
			singleAdapter: false,
			multiLine: false
		}
	},
	mutations: {
		[ UPDATE_SETTINGS ] (state, payload) {
			state.fetching = payload.fetching
			state.error = payload.error
			if (payload.data) {
				state.data = { ...state.data, ...payload.data }
			}
		},
		[ UPDATE_REFRESH_RATE ] (state, refreshRate) {
			if (refreshRate === undefined || typeof refreshRate !== 'number') return
			state.data.refreshRate = refreshRate
		},
		[ UPDATE_SINGLE_ADAPTER ] (state, singleAdapter) {
			if (singleAdapter === undefined || typeof singleAdapter !== 'boolean') return
			state.data.singleAdapter = singleAdapter
		},
		[ UPDATE_MULTI_LINE ] (state, multiLine) {
			if (multiLine === undefined || typeof multiLine !== 'boolean') return
			state.data.multiLine = multiLine
		}
	},
	actions: {
		[ FETCH_SETTINGS ] ({ dispatch }) {
			dispatch(REQUEST_API, {
				rule: 'settings',
				type: UPDATE_SETTINGS
			})
		},
		[ SAVE_SETTINGS ] ({ dispatch, state }) {
			dispatch(REQUEST_API, {
				rule: 'settings',
				method: 'POST',
				data: state.data
			})
		}
	}
}