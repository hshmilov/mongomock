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
export const GET_ALL_USERS = 'GET_ALL_USERS'
export const UPDATE_ALL_USERS = 'UPDATE_ALL_USERS'
export const CHANGE_PASSWORD = 'CHANGE_PASSWORD'
export const CHANGE_PERMISSIONS = 'CHANGE_PERMISSIONS'
export const CREATE_USER = 'CREATE_USER'
export const REMOVE_USER = 'REMOVE_USER'


export const auth = {
	state: {
		currentUser: { fetching: false, data: { }, error: '' },
		allUsers: { fetching: false, data: { }, error: '' }
	},
	mutations: {
		[ SET_USER ] (state, payload) {
			state.currentUser.fetching = payload.fetching
			state.currentUser.error = payload.error
			if (payload.data) {
				state.currentUser.data = { ...payload.data }
			}
		},
		[ INIT_USER ] (state, payload) {
			state.currentUser.fetching = payload.fetching
			state.currentUser.error = payload.error
			if (!state.currentUser.fetching) {
				state.currentUser.data = {}
			}
		},
		[ INIT_ERROR ] (state) {
			state.currentUser.error = ''
		},
		[ UPDATE_ALL_USERS ] (state, payload) {
            state.allUsers.fetching = payload.fetching
            state.allUsers.error = payload.error
            if (payload.data) {
                state.allUsers.data = [ ...payload.data ]
            }
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
				if (window.location.pathname !== '/') window.location.pathname = '/'
			})
		},
		[ GET_ALL_USERS ] ({dispatch}) {
			/*
				Request from server to login a user according to its Google token id
			 */
			return dispatch(REQUEST_API, {
				rule: 'authusers',
				type: UPDATE_ALL_USERS
			})
		},
		[ CHANGE_PASSWORD ] ({dispatch, commit}, payload) {
			/*
				Request from server to login a user according to its Google token id
			 */
			if (!payload || !payload.user_name || !payload.old_password || !payload.new_password || !payload.source) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: 'authusers',
				method: 'POST',
				data: payload
			})
		},
		[ CHANGE_PERMISSIONS ] ({ dispatch }, payload) {
			/*
				Request from server to change permissions for an existing user
			 */
			if (!payload || !payload.user_name || !payload.permissions || !payload.source) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: 'edit_foreign_user',
				method: 'POST',
				data: payload
			})
		},
		[ CREATE_USER ] ({ dispatch }, payload) {
			/*
				Request from server to login a add a new user
			 */
			if (!payload || !payload.user_name) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: 'edit_foreign_user',
				method: 'PUT',
				data: payload
			})
		},
		[ REMOVE_USER ] ({ dispatch }, payload) {
            /*
                Request from server to remove a user
             */
            if (!payload || !payload.user_name) {
                return
            }
            return dispatch(REQUEST_API, {
                rule: 'edit_foreign_user',
                method: 'DELETE',
                data: payload
            })
		}
	}
}