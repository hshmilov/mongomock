import { REQUEST_API } from '../actions'

export const GET_USER = 'GET_USER'
export const LOGIN = 'LOGIN'
export const LDAP_LOGIN = 'LDAP_LOGIN'
export const GOOGLE_LOGIN = 'GOOGLE_LOGIN'
export const SET_USER = 'SET_USER'
export const LOGOUT = 'LOGOUT'
export const INIT_USER = 'INIT_USER'
export const INIT_ERROR = 'INIT_ERROR'
export const GET_LOGIN_OPTIONS = 'GET_LOGIN_OPTIONS'
export const CHANGE_PASSWORD = 'CHANGE_PASSWORD'


export const auth = {
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
				state.data = { ...payload.data }
			}
		},
		[ INIT_USER ] (state, payload) {
			state.fetching = payload.fetching
			state.error = payload.error
			if (!state.fetching) {
				state.data = {}
			}
		},
		[ INIT_ERROR ] (state) {
			state.error = ''
		}
	},
	actions: {
		[ GET_USER ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'login',
				type: SET_USER
			})
		} ,
		[ GET_LOGIN_OPTIONS ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'get_login_options',
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
				rule: 'login',
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
		[ LDAP_LOGIN ] ({dispatch, commit}, payload) {
			/*
				Request from server to login a user according to given credentials.
				A valid user name and its password is required.
			 */
			if (!payload || !payload.user_name || !payload.password || !payload.domain) {
				return
			}
			dispatch(REQUEST_API, {
				rule: 'ldap-login',
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
		[ GOOGLE_LOGIN ] ({dispatch, commit}, payload) {
			/*
				Request from server to login a user according to its Google token id
			 */
			if (!payload || !payload.id_token) {
				return
			}
			dispatch(REQUEST_API, {
				rule: 'google-login',
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
			try {
                const auth2 = window.gapi.auth2.getAuthInstance()
                auth2.signOut()
            }
			catch (err) {
			}

			dispatch(REQUEST_API, {
				rule: 'logout',
				type: INIT_USER
			}).then(() => {
				// this is needed because google login only works from top page
            	if (window.location.pathname != '/') window.location.pathname = '/'
			})
		},
		[ CHANGE_PASSWORD ] ({dispatch, commit}, payload) {
			/*
				Request from server to login a user according to its Google token id
			 */
			if (!payload || !payload.user_name || !payload.old_password || !payload.new_password) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: 'authusers',
				method: 'POST',
				data: payload
			})
		},
	}
}