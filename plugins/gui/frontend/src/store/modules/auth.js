/* eslint-disable no-param-reassign */
import _get from 'lodash/get';
import _keyBy from 'lodash/keyBy';

import { SHOULD_SHOW_CLOUD_COMPLIANCE } from '@store/modules/settings';
import { REQUEST_API } from '../actions';
import { RESET_DEVICES_STATE } from './devices';
import { RESET_USERS_STATE } from './users';
import { RESET_REPORTS_STATE } from './reports';
import {
  RESET_TUNNEL_CONNECTION_CHECKING,
} from '@store/modules/dashboard';
import { getPermissionsStructure } from '@constants/permissions';
import {ACCESS_TOKEN, REFRESH_TOKEN} from "@constants/session_utils";

export const UPDATE_EXISTING_USER = 'UPDATE_EXISTING_USER';
export const GET_SYSTEM_USERS_MAP = 'GET_SYSTEM_USERS_MAP';
export const GET_SYSTEM_ROLES_MAP = 'GET_SYSTEM_ROLES_MAP';
export const GET_ALL_SYSTEM_USERS_NAMES = 'GET_ALL_SYSTEM_USERS_NAMES';
export const ADD_NEW_USER = 'ADD_NEW_USER';
export const GET_USER = 'GET_USER';
export const LOGIN = 'LOGIN';
export const LOGOUT = 'LOGOUT';
export const LDAP_LOGIN = 'LDAP_LOGIN';
export const SET_USER = 'SET_USER';
export const SET_LOGIN_OPTIONS = 'SET_LOGIN_OPTIONS';
export const INIT_USER = 'INIT_USER';
export const SET_USER_ERROR = 'SET_USER_ERROR';
export const GET_LOGIN_OPTIONS = 'GET_LOGIN_OPTIONS';
export const GET_ALL_USERS = 'GET_ALL_USERS';
export const UPDATE_ALL_USERS = 'UPDATE_ALL_USERS';
export const CHANGE_PASSWORD = 'CHANGE_PASSWORD';
export const SUBMIT_SIGNUP = 'SUBMIT_SIGNUP';
export const GET_SIGNUP = 'GET_SIGNUP';
export const UPDATE_SIGNUP = 'UPDATE_SIGNUP';
export const CREATE_USER = 'CREATE_USER';
export const UPDATE_USER = 'UPDATE_USER';
export const REMOVE_USERS = 'REMOVE_USERS';
export const UPDATE_USERS_ROLE = 'UPDATE_USERS_ROLE';

export const ADD_NEW_ROLE = 'ADD_NEW_ROLE';
export const UPDATE_EXISTING_ROLE = 'UPDATE_EXISTING_ROLE';
export const REMOVE_ROLE = 'REMOVE_ROLE';


export const GET_ALL_ROLES = 'GET_ALL_ROLES';
export const UPDATE_ALL_ROLES = 'UPDATE_ALL_ROLES';
export const CREATE_ROLE = 'CREATE_ROLE';
export const CHANGE_ROLE = 'CHANGE_ROLE';

export const GET_ADMIN_USER_ID = 'GET_ADMIN_USER_ID';

export const IS_USER_ADMIN = 'IS_USER_ADMIN';
export const IS_AXONIUS_USER = 'IS_AXONIUS_USER';

export const GET_PERMISSION_STRUCTURE = 'GET_PERMISSION_STRUCTURE';

export const NOT_LOGGED_IN = 'Not logged in';
export const REFRESH_ACCESS_TOKEN = 'REFRESH_ACCESS_TOKEN';

export const auth = {
  state: {
    currentUser: { fetching: false, data: null, error: '' },
    loginOptions: { fetching: false, data: null, error: '' },
    allUsers: {
      content: { data: [], fetching: false, error: '' },

      count: {
        data: 0,
        fetching:
          false,
        error: '',
        data_to_show: 0,
      },

      view: {
        page: 0,
        pageSize: 20,
        coloumnSizes: [],
        query: {
          filter: '', expressions: [],
        },
        sort: {
          field: '', desc: true,
        },
      },
    },
    allRoles: { fetching: false, data: [], error: '' },
    defaultRole: { fetching: false, data: '', error: '' },
    signup: { fetching: false, data: null, error: '' },
  },
  getters: {
    [IS_USER_ADMIN](state) {
      const user = state.currentUser.data;
      return (user.role_name === 'Admin' || user.role_name === 'Owner') && user.predefined;
    },
    [IS_AXONIUS_USER](state) {
      const user = state.currentUser.data;
      return user.is_axonius_role && user.predefined;
    },
    getCurrentUserPermissions(state) {
      return _get(state, 'currentUser.data.permissions');
    },
    [GET_SYSTEM_USERS_MAP](state) {
      const users = _get(state, 'allUsers.content.data', []);
      return _keyBy(users, 'uuid');
    },
    [GET_SYSTEM_ROLES_MAP](state) {
      const roles = _get(state, 'allRoles.data', []);
      const val = _keyBy(roles, 'uuid');
      return val;
    },
    [GET_ALL_SYSTEM_USERS_NAMES](state) {
      const users = _get(state, 'allUsers.content.data', []);
      return users.filter((u) => u).map((u) => u.user_name);
    },
    [GET_ADMIN_USER_ID](state) {
      const users = _get(state, 'allUsers.content.data', []);
      const admin = users.find((user) => user.user_name === 'admin') || {};
      return admin.uuid;
    },
    [GET_PERMISSION_STRUCTURE](state, getters) {
      return getPermissionsStructure(getters[SHOULD_SHOW_CLOUD_COMPLIANCE]);
    },
  },
  mutations: {
    [SET_USER](state, payload) {
      state.currentUser.fetching = payload.fetching;
      state.currentUser.error = payload.error;
      if (payload.data) {
        delete state.currentUser.userTimedOut;
        state.currentUser.data = { ...payload.data };
      } else if (payload.userTimedOut) {
        state.currentUser.userTimedOut = true;
        state.currentUser.data = null;
        state.currentUser.error = 'Session timed out';
      }
    },
    [SET_LOGIN_OPTIONS](state, payload) {
      state.loginOptions.fetching = payload.fetching;
      state.loginOptions.error = payload.error;
      if (payload.data) {
        state.loginOptions.data = { ...payload.data };
      }
    },
    [INIT_USER](state, payload) {
      const { fetching, error } = payload;
      state.currentUser.fetching = fetching;
      if (error !== NOT_LOGGED_IN) {
        state.currentUser.error = error;
      }
      if (!state.currentUser.fetching) {
        state.currentUser.data = {};
      }
    },
    [SET_USER_ERROR](state, payload) {
      state.currentUser.error = payload.error;
    },
    [UPDATE_ALL_USERS](state, payload) {
      state.allUsers.content.fetching = payload.fetching;
      state.allUsers.content.error = payload.error;
      state.allUsers.count.fetching = payload.fetching;
      state.allUsers.count.error = payload.fetching;

      if (payload.data) {
        state.allUsers.content.data = [...payload.data];
        state.allUsers.count.data = payload.data.length;
      }
    },
    [UPDATE_ALL_ROLES](state, payload) {
      state.allRoles.fetching = payload.fetching;
      state.allRoles.error = payload.error;
      if (payload.data) {
        state.allRoles.data = [...payload.data];
      }
    },
    [UPDATE_SIGNUP](state, payload) {
      state.signup.fetching = payload.fetching;
      state.signup.error = payload.error;
      if (payload.data) {
        state.signup.data = payload.data.signup;
      }
    },
    [ADD_NEW_USER](state, payload) {
      const { error, fetching, data } = payload;
      state.allUsers.content.fetching = fetching;
      if (!error && data) {
        state.allUsers.content.data.push(data);
        state.allUsers.count.data = state.allUsers.content.data.length;
        state.allUsers.count.data_to_show = state.allUsers.content.data.length;
      }
    },
    [UPDATE_EXISTING_USER](state, payload) {
      const { error, fetching, data } = payload;
      state.allUsers.content.fetching = fetching;
      if (!error && data) {
        const { user, uuid } = data;
        const currentUsersState = _get(state, 'allUsers.content.data', []);
        state.allUsers.content.data = currentUsersState.map((u) => {
          if (u.uuid === uuid) {
            return user;
          }
          return u;
        });
      }
    },
    [REMOVE_USERS](state, payload) {
      const { ids, include } = payload;
      const currentUsersState = _get(state, 'allUsers.content.data', []);
      if (!include) {
        state.allUsers.content.data = currentUsersState.filter((u) => u.user_name === 'admin' || ids.includes(u.uuid));
      } else {
        state.allUsers.content.data = currentUsersState.filter((u) => !ids.includes(u.uuid));
      }
      state.allUsers.count.data = state.allUsers.content.data.length;
      state.allUsers.count.data_to_show = state.allUsers.content.data.length;

    },
    [UPDATE_USERS_ROLE](state, { roleId, ids, include }) {
      const currentUsersState = _get(state, 'allUsers.content.data', []);
      if (!include) {
        state.allUsers.content.data = currentUsersState.map((u) => {
          if (u.user_name !== 'admin' && !ids.includes(u.uuid)) {
            return {
              ...u,
              last_updated: Date.now(),
              role_id: roleId,
            };
          }
          return u;
        });
      } else {
        state.allUsers.content.data = currentUsersState.map((u) => {
          if (ids.includes(u.uuid)) {
            return {
              ...u,
              role_id: roleId,
            };
          }
          return u;
        });
      }
    },
    [ADD_NEW_ROLE](state, payload) {
      const { error, fetching, data } = payload;
      state.allRoles.fetching = fetching;
      if (error) {
        state.allRoles.error = error;
      } else if (data) {
        state.allRoles.data.push(data);
        state.allRoles.count = state.allRoles.data.length;
      }
    },
    [UPDATE_EXISTING_ROLE](state, payload) {
      const { error, fetching, data } = payload;
      state.allRoles.fetching = fetching;
      if (!error && data) {
        const role = data;
        const currentRolesState = _get(state, 'allRoles.data', []);
        state.allRoles.data = currentRolesState.map((r) => {
          if (r.uuid === role.uuid) {
            return role;
          }
          return r;
        });
      }
    },
    [REMOVE_ROLE](state, payload) {
      const { error, fetching, uuid } = payload;
      if (!fetching && !error) {
        const currentRolesState = _get(state, 'allRoles.data', []);
        state.allRoles.data = currentRolesState.filter((u) => uuid !== u.uuid);
        state.allRoles.count = state.allRoles.data.length;
      }
    },
  },
  actions: {
    [GET_USER]({ dispatch }) {
      return dispatch(REQUEST_API, {
        rule: 'login',
        type: SET_USER,
      });
    },
    [GET_LOGIN_OPTIONS]({ dispatch }) {
      return dispatch(REQUEST_API, {
        rule: 'get_login_options',
        type: SET_LOGIN_OPTIONS,
      });
    },
    [REFRESH_ACCESS_TOKEN]({ dispatch }) {
      dispatch(REQUEST_API, {
        rule: 'token/refresh',
        method: 'GET',
      }).then((response) => {
        if (response.status === 200) {
          localStorage.setItem(ACCESS_TOKEN, response.data.access_token);
        }
      });
    },
    [LOGIN]({ dispatch, commit }, payload) {
      /*
        Request from server to login a user according to given credentials.
        A valid user name and its password is required.
       */
      return new Promise((resolve, reject) => {
        if (!payload || ((!payload.user_name || !payload.password) && !payload.saml_token)) {
          reject(new Error('user_name & password are must'));
        }

        dispatch(REQUEST_API, {
          rule: 'login',
          method: 'POST',
          data: payload,
        }).then((response) => {
          if (!response || !response.status) {
            reject(commit(SET_USER, { error: 'Login failed.' }));
          } else if (response.status === 200) {
            localStorage.setItem(ACCESS_TOKEN, response.data.access_token);
            localStorage.setItem(REFRESH_TOKEN, response.data.refresh_token);
            commit(RESET_TUNNEL_CONNECTION_CHECKING);
            resolve(dispatch(GET_USER));
          } else {
            reject(commit(SET_USER, { error: response.data.message, fetching: false }));
          }
        }).catch((error) => {
          commit(SET_USER, { error: error.response.data.message });
          reject(error);
        });
      });
    },
    [LDAP_LOGIN]({ dispatch, commit }, payload) {
      /*
        Request from server to login a user according to given credentials.
        A valid user name and its password is required.
       */
      if (!payload || !payload.user_name || !payload.password || !payload.domain) {
        return;
      }
      dispatch(REQUEST_API, {
        rule: 'login/ldap',
        method: 'POST',
        data: payload,
      }).then((response) => {
        if (!response || !response.status) {
          commit(SET_USER, { error: 'Login failed.' });
        } else if (response.status === 200) {
          localStorage.setItem(ACCESS_TOKEN, response.data.access_token);
          localStorage.setItem(REFRESH_TOKEN, response.data.refresh_token);
          dispatch(GET_USER);
        } else {
          commit(SET_USER, { error: response.data.message, fetching: false });
        }
      }).catch((error) => {
        commit(SET_USER, { error: error.response.data.message });
      });
    },
    [LOGOUT]({ dispatch, commit }, payload) {
      try {
        const auth2 = window.gapi.auth2.getAuthInstance();
        auth2.signOut();
      } catch (err) {}
      return dispatch(REQUEST_API, {
        rule: 'logout',
      }).then(() => {
        localStorage.removeItem(ACCESS_TOKEN);
        localStorage.removeItem(REFRESH_TOKEN);
        commit(RESET_DEVICES_STATE);
        commit(RESET_USERS_STATE);
        commit(RESET_REPORTS_STATE);
        commit(SET_USER, {
          ...payload,
          fetching: false,
          error: '',
          data: null,
        });
        Promise.resolve();
      });
    },
    [GET_ALL_USERS]({ dispatch }) {
      /*
        Request from server to get a list of all users of the system
       */
      return dispatch(REQUEST_API, {
        rule: 'settings/users',
        type: UPDATE_ALL_USERS,
      });
    },
    [CHANGE_PASSWORD]({ dispatch }, payload) {
      /*
        Request from server to login a user according to its Google token id
       */
      if (!payload || !payload.oldPassword || !payload.newPassword) {
        return;
      }
      return dispatch(REQUEST_API, {
        rule: 'self/password',
        method: 'POST',
        data: {
          new: payload.newPassword,
          old: payload.oldPassword,
        },
      });
    },
    [SUBMIT_SIGNUP]({ dispatch }, payload) {
      if (!payload) {
        return;
      }
      return dispatch(REQUEST_API, {
        rule: 'signup',
        method: 'POST',
        data: payload,
      });
    },

    [GET_SIGNUP]({ dispatch }) {
      return dispatch(REQUEST_API, {
        rule: 'signup',
        method: 'GET',
        type: UPDATE_SIGNUP,
      });
    },

    [CREATE_USER]({ dispatch }, payload) {
      /*
        Request from server to login a add a new user
       */
      if (!payload || !payload.user_name) {
        return Promise.reject(new Error('username is a required field'));
      }
      return dispatch(REQUEST_API, {
        rule: 'settings/users',
        method: 'PUT',
        data: payload,
        type: ADD_NEW_USER,
      });
    },
    [UPDATE_USER]({ dispatch }, payload) {
      /*
        Request from server to update an existing user
       */
      if (!payload || !payload.uuid) {
        return Promise.reject(new Error('uuid is a required field'));
      }
      return dispatch(REQUEST_API, {
        rule: `settings/users/${payload.uuid}`,
        method: 'POST',
        data: payload.user,
        type: UPDATE_EXISTING_USER,
      });
    },
    [REMOVE_USERS]({ dispatch, commit }, payload) {
      /*
          Request from server to remove a user
       */
      if (!payload || !Array.isArray(payload.ids)) {
        return Promise.reject(new Error('ids[] should be supplied'));
      }
      return dispatch(REQUEST_API, {
        rule: payload.ids.length > 1 ? 'settings/users/bulk' : `settings/users/${payload.ids[0]}`,
        method: 'DELETE',
        data: payload,
      }).then((res) => {
        if (res.status === 200) {
          commit(REMOVE_USERS, payload);
        } else if (res.status === 202) {
          // request partially succeeded
          dispatch(GET_ALL_USERS);
        }
      });
    },
    [GET_ALL_ROLES]({ dispatch }) {
      /*
          Request from server to login a user according to its Google token id
       */
      return dispatch(REQUEST_API, {
        rule: 'settings/roles',
        type: UPDATE_ALL_ROLES,
      });
    },
    [CREATE_ROLE]({ dispatch }, payload) {
      /*
          Request from server to save a role (may be new or existing)
       */
      if (!payload || !payload.name || !payload.permissions) {
        return;
      }
      return dispatch(REQUEST_API, {
        rule: 'settings/roles',
        method: 'PUT',
        data: payload,
        type: ADD_NEW_ROLE,
      });
    },
    [CHANGE_ROLE]({ dispatch }, payload) {
      /*
          Request from server to save a role (may be new or existing)
       */
      if (!payload || !payload.uuid || !payload.name || !payload.permissions) {
        return null;
      }
      return dispatch(REQUEST_API, {
        rule: `settings/roles/${payload.uuid}`,
        method: 'POST',
        data: payload,
        type: UPDATE_EXISTING_ROLE,
      });
    },
    [REMOVE_ROLE]({ dispatch }, payload) {
      if (!payload || !payload.uuid) {
        return null;
      }
      return dispatch(REQUEST_API, {
        rule: `settings/roles/${payload.uuid}`,
        method: 'DELETE',
        type: REMOVE_ROLE,
        payload,
      });
    },
    [UPDATE_USERS_ROLE]({ dispatch, commit }, payload) {
      const { ids, include, roleId } = payload;
      if (!roleId) {
        return Promise.reject(new Error('roleId is a mandatory parameter'));
      }
      return dispatch(REQUEST_API, {
        rule: 'settings/users/bulk/assign_role',
        method: 'POST',
        data: { ids, include, role_id: roleId },
      }).then((res) => {
        if (res.status === 200) {
          commit(UPDATE_USERS_ROLE, { ids, roleId, include });
        } else if (res.status === 202) {
          dispatch(GET_ALL_USERS);
        }
      });
    },
  },
};
