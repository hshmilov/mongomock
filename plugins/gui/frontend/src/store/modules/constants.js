import { REQUEST_API } from '../actions'

export const FETCH_CONSTANTS = 'FETCH_CONSTANTS'
export const SET_CONSTANTS = 'SET_CONSTANTS'

export const FETCH_FIRST_HISTORICAL_DATE = 'FETCH_FIRST_HISTORICAL_DATE'
export const SET_FIRST_HISTORICAL_DATE = 'SET_FIRST_HISTORICAL_DATE'

export const FETCH_ALLOWED_DATES = 'FETCH_ALLOWED_DATES'
export const SET_ALLOWED_DATES = 'SET_ALLOWED_DATES'

export const constants = {
	state: {
		constants: {},
		firstHistoricalDate: {},
		allowedDates: {}
	},
	mutations: {
		[ SET_CONSTANTS ] (state, payload) {
			if (payload.data) {
				state.constants = { ...payload.data }
			}
		},
		[ SET_FIRST_HISTORICAL_DATE ] (state, payload) {
			if (payload.data) {
				state.firstHistoricalDate = payload.data
			}
		},
		[ SET_ALLOWED_DATES ] (state, payload) {
			if (payload.data) {
				state.allowedDates = { ...payload.data }
			}
		},
	},
	actions: {
		[ FETCH_CONSTANTS ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'get_constants',
				type: SET_CONSTANTS
			})
		},
		[ FETCH_FIRST_HISTORICAL_DATE ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'first_historical_date',
				type: SET_FIRST_HISTORICAL_DATE
			})
		},
		[ FETCH_ALLOWED_DATES ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'get_allowed_dates',
				type: SET_ALLOWED_DATES
			})
		},
	}
}