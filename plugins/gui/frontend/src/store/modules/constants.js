import { REQUEST_API } from '../actions'

export const FETCH_CONSTANTS = 'FETCH_CONSTANTS'
export const SET_CONSTANTS = 'SET_CONSTANTS'

export const constants = {
	state: {
		fetching: false,
		data: { },
		error: ''
	},
	mutations: {
		[ SET_CONSTANTS ] (state, payload) {
			state.fetching = payload.fetching
			state.error = payload.error
			if (payload.data) {
				state.data = { ...payload.data }
			}
		},
	},
	actions: {
		[ FETCH_CONSTANTS ] ({dispatch}) {
			/*
				Request from server to login a user according to its Google token id
			 */
			return dispatch(REQUEST_API, {
				rule: 'get_constants',
				type: SET_CONSTANTS
			})
		},
	}
}