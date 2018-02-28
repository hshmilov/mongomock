import { REQUEST_API } from '../actions'

export const FETCH_LIFECYCLE = 'FETCH_LIFECYCLE'
export const UPDATE_LIFECYCLE = 'UPDATE_LIFECYCLE'

export const dashboard = {
	state: {
		lifecycle: { data: {}, fetching: false, error: ''}
	},
	mutations: {
		[ UPDATE_LIFECYCLE ] (state, payload) {
			state.lifecycle.fetching = payload.fetching
			state.lifecycle.error = payload.error
			if (payload.data && payload.data.stages) {
				state.lifecycle.data = { ...payload.data }
			}
		}
	},
	actions: {
		[ FETCH_LIFECYCLE ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: 'api/dashboard/lifecycle',
				type: UPDATE_LIFECYCLE
			})
		}
	}
}