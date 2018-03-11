import { REQUEST_API } from '../actions'

export const FETCH_USER_FIELDS = 'FETCH_USER_FIELDS'
export const UPDATE_USER_FIELDS = 'UPDATE_USER_FIELDS'

export const user = {
	state: {
		dataTable: {
			content: {data: [], fetching: false, error: ''},
			count: {data: 0, fetching: false, error: ''},
			view: {
				page: 0, pageSize: 20, fields: [
					'specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
					'specific_data.data.last_seen', 'specific_data.data.is_admin',
				], coloumnSizes: [], filter: '', sort: {field: '', desc: true}
			}
		},
		userFields: {data: [], fetching: false, error: ''}
	},
	mutations: {
		[ UPDATE_USER_FIELDS ] (state, payload) {
			state.userFields.fetching = payload.fetching
			state.userFields.error = payload.error
			if (!payload.fetching) {
				state.userFields.data = payload.data
				state.userFields.data.generic.name = 'specific_data.data'
				if (state.userFields.data.specific) {
					Object.keys(state.userFields.data.specific).forEach((specificKey) => {
						state.userFields.data.specific[specificKey].name = `adapters_data.${specificKey}`
					})
				}
			}
		},
	},
	actions: {
		[ FETCH_USER_FIELDS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `user/fields`,
				type: UPDATE_USER_FIELDS
			})
		}
	}
}