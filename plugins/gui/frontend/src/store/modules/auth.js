import { REQUEST_API } from '../actions'

export const GET_USER = 'GET_USER'
export const GET_OIDC_ID_TOKEN ='GET_OIDC_ID_TOKEN'
export const SET_OIDC_ID_TOKEN = 'SET_OIDC_ID_TOKEN'
export const LOGIN = 'LOGIN'
export const LDAP_LOGIN = 'LDAP_LOGIN'
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

export const GET_ALL_ROLES = 'GET_ALL_ROLES'
export const UPDATE_ALL_ROLES = 'UPDATE_ALL_ROLES'
export const CREATE_ROLE = 'CREATE_ROLE'
export const CHANGE_ROLE = 'CHANGE_ROLE'
export const REMOVE_ROLE = 'REMOVE_ROLE'

export const GET_DEFAULT_ROLE = 'GET_DEFAULT_ROLE'
export const SET_DEFAULT_ROLE = 'SET_DEFAULT_ROLE'
export const UPDATE_DEFAULT_ROLE = 'UPDATE_DEFAULT_ROLE'


export const auth = {
	state: {
		currentUser: { fetching: false, data: { }, error: '' },
		allUsers: { fetching: false, data: [], error: '' },
        allRoles: { fetching: false, data: [], error: '' },
		defaultRole: { fetching: false, data: '', error: '' },
		oktaIdToken: { fetching: false, data: '', error: '' }
	},
	mutations: {
		[ SET_USER ] (state, payload) {
			state.currentUser.fetching = payload.fetching
			state.currentUser.error = payload.error
			if (payload.data) {
				state.currentUser.data = { ...payload.data }
			}
		},
		[ SET_OIDC_ID_TOKEN ] (state, payload) {
			state.currentUser.fetching = payload.fetching
			state.currentUser.error = payload.error
			if (payload.data) {
				state.oktaIdToken.data = payload.data
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
		},
        [ UPDATE_ALL_ROLES ] (state, payload) {
            state.allRoles.fetching = payload.fetching
            state.allRoles.error = payload.error
            if (payload.data) {
                state.allRoles.data = [ ...payload.data ]
            }
        },
		[ SET_DEFAULT_ROLE ] (state, payload) {
            state.defaultRole.fetching = payload.fetching
            state.defaultRole.error = payload.error
            if (payload.data) {
                state.defaultRole.data = payload.data
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
		[ GET_OIDC_ID_TOKEN ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'get_oidc_id_token',
				type: SET_OIDC_ID_TOKEN
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
				rule: 'login/ldap',
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
			})
		},
		[ GET_ALL_USERS ] ({dispatch}) {
			/*
				Request from server to get a list of all users of the system
			 */
			return dispatch(REQUEST_API, {
				rule: 'system/users',
				type: UPDATE_ALL_USERS
			})
		},
		[ CHANGE_PASSWORD ] ({dispatch}, payload) {
			/*
				Request from server to login a user according to its Google token id
			 */
			if (!payload || !payload.uuid || !payload.oldPassword || !payload.newPassword) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: `system/users/${payload.uuid}/password`,
				method: 'POST',
				data: {
					new: payload.newPassword,
					old: payload.oldPassword
                }
			})
		},
		[ CHANGE_PERMISSIONS ] ({ dispatch }, payload) {
			/*
				Request from server to change permissions for an existing user
			 */
			if (!payload || !payload.uuid || !payload.permissions) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: `system/users/${payload.uuid}/access`,
				method: 'POST',
				data: {
					permissions: payload.permissions,
					role_name: payload.role_name
				}
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
				rule: 'system/users',
				method: 'PUT',
				data: payload
			})
		},
		[ REMOVE_USER ] ({ dispatch }, payload) {
            /*
                Request from server to remove a user
             */
            if (!payload || !payload.uuid) {
                return
            }
            return dispatch(REQUEST_API, {
                rule: `system/users/${payload.uuid}`,
                method: 'DELETE'
            })
		},
        [ GET_ALL_ROLES ] ({ dispatch }) {
            /*
                Request from server to login a user according to its Google token id
             */
            return dispatch(REQUEST_API, {
                rule: 'roles',
                type: UPDATE_ALL_ROLES
            })
        },
        [ CREATE_ROLE ] ({ dispatch }, payload) {
            /*
                Request from server to save a role (may be new or existing)
             */
            if (!payload || !payload.name || !payload.permissions) {
                return
            }
            return dispatch(REQUEST_API, {
                rule: 'roles',
                method: 'PUT',
                data: payload
            })
        },
        [ CHANGE_ROLE ] ({ dispatch }, payload) {
            /*
                Request from server to save a role (may be new or existing)
             */
            if (!payload || !payload.name || !payload.permissions) {
                return
            }
            return dispatch(REQUEST_API, {
                rule: 'roles',
                method: 'POST',
                data: payload
            })
        },
        [ REMOVE_ROLE ] ({ dispatch }, payload) {
            if (!payload || !payload.name) {
                return
            }
            return dispatch(REQUEST_API, {
                rule: 'roles',
                method: 'DELETE',
                data: payload
            })
        },
		[ GET_DEFAULT_ROLE ] ({ dispatch }) {
			return dispatch(REQUEST_API, {
				rule: 'roles/default',
				type: SET_DEFAULT_ROLE
			})
		},
		[ UPDATE_DEFAULT_ROLE ] ({ dispatch }, payload) {
			if (!payload || !payload.name) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: 'roles/default',
				method: 'POST',
				data: payload
			})
		}
	}
}