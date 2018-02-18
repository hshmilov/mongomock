import { REQUEST_API } from '../actions'

export const GET_USER = 'GET_USER'
export const LOGIN = 'LOGIN'
export const SET_USER = 'SET_USER'
export const LOGOUT = 'LOGOUT'
export const INIT_USER = 'INIT_USER'

const USER_IMAGE_PATH = '/src/assets/images/users/'

export const user = {
	state: {
		fetching: false,
		data: { },
		error: ''
	},
	mutations: {
		[ SET_USER ] (state, payload) {
			state.fetching = payload.fetching
			state.error = payload.error
			if (payload.data) {
				state.data = { ...payload.data,
					pic_name: `${USER_IMAGE_PATH}${payload.data.pic_name}`
				}
			}
		},
		[ INIT_USER ] (state, payload) {
			state.fetching = payload.fetching
			state.error = payload.error
			if (!state.fetching) {
				state.data = {}
			}
		}
	},
	actions: {
		[ GET_USER ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: '/api/login',
				type: SET_USER
			})
		} ,
		[ LOGIN ] ({dispatch, commit}, payload) {
			/*
				Request from server to login a user according to given credentials.
				A valid user name and its password is required.
			 */
			if (!payload || !payload.user_name || !payload.password) {
				return
			}
			dispatch(REQUEST_API, {
				rule: '/api/login',
				method: 'POST',
				data: payload
			}).then((response) => {
				if (!response || !response.status) {
					commit(SET_USER, { error: 'Login failed.'})

				} else if (response.status === 200) {
					dispatch(GET_USER)
				} else {
					commit(SET_USER, { error: response.data.message, fetching: false })
				}
			}).catch((error) => {
				commit(SET_USER, { error: error.response.data.message})
			})
		},
		[ LOGOUT ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: 'api/logout',
				type: INIT_USER
			})
		}
	}
}