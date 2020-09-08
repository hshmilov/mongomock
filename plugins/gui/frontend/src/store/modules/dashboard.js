import { RESET_DEVICES_MERGED_DATA_BY_ID } from '@store/modules/devices';
import { tunnelConnectionStatuses } from '@constants/settings';
import _pick from 'lodash/pick';
import { REQUEST_API, downloadFile } from '../actions';

export const FETCH_LIFECYCLE = 'FETCH_LIFECYCLE';
export const UPDATE_LIFECYCLE = 'UPDATE_LIFECYCLE';

export const FETCH_DISCOVERY_DATA = 'FETCH_DISCOVERY_DATA';

export const FETCH_DASHBOARD_SPACES = 'FETCH_DASHBOARD_SPACES';
export const UPDATE_DASHBOARD_SPACES = 'UPDATE_DASHBOARD_SPACES';

export const SAVE_DASHBOARD_SPACE = 'SAVE_DASHBOARD_SPACE';
export const UPDATE_ADDED_SPACE = 'UPDATE_ADDED_SPACE';
export const CHANGE_DASHBOARD_SPACE = 'CHANGE_DASHBOARD_SPACE';
export const UPDATE_CHANGED_SPACE = 'UPDATE_CHANGED_SPACE';
export const REMOVE_DASHBOARD_SPACE = 'REMOVE_DASHBOARD_SPACE';
export const UPDATE_REMOVED_SPACE = 'UPDATE_REMOVED_SPACE';

export const SAVE_DASHBOARD_PANEL = 'SAVE_DASHBOARD_PANEL';
export const CHANGE_DASHBOARD_PANEL = 'CHANGE_DASHBOARD_PANEL';
export const REMOVE_DASHBOARD_PANEL = 'REMOVE_DASHBOARD_PANEL';
export const UPDATE_REMOVED_PANEL = 'UPDATE_REMOVED_PANEL';

export const SAVE_REORDERED_PANELS = 'SAVE_REORDERED_PANELS';
export const UPDATE_DASHBOARDS_ORDER = 'UPDATE_DASHBOARDS_ORDER';
export const CHANGE_PANEL_SPACE = 'CHANGE_PANEL_SPACE';

export const FETCH_CHART_CSV = 'FETCH_CHART_CSV';

export const MOVE_OR_COPY_TOGGLE = 'MOVE_OR_COPY_TOGGLE';
export const MOVE_PANEL = 'MOVE_PANEL';
export const COPY_PANEL = 'COPY_PANEL';
export const RESET_DASHBOARD_SORT = 'RESET_DASHBOARD_SORT';
export const TOGGLE_TUNNEL_CONNECTION_MODAL = 'TOGGLE_TUNNEL_CONNECTION_MODAL';
export const RESET_TUNNEL_CONNECTION_CHECKING = 'RESET_TUNNEL_CONNECTION_CHECKING';

export const GET_SPACE_BY_ID = 'GET_SPACE_BY_ID';

export const dashboard = {
  state: {
    lifecycle: { data: {}, fetching: false, error: '' },
    spaces: { data: [], fetching: false, error: '' },
    tunnelDisconnected: false,
  },
  mutations: {
    [UPDATE_LIFECYCLE](state, payload) {
      state.lifecycle.fetching = payload.fetching;
      state.lifecycle.error = payload.error;

      if (payload.data && payload.data.sub_phases) {
        state.lifecycle.data = {
          subPhases: payload.data.sub_phases,
          nextRunTime: payload.data.next_run_time,
          status: payload.data.status,
          lastStartTime: payload.data.last_start_time,
          lastFinishedTime: payload.data.last_finished_time,
          tunnelStatus: payload.data.tunnel_status,
        };
      }
    },
    [UPDATE_DASHBOARD_SPACES](state, payload) {
      state.spaces.fetching = payload.fetching;
      state.spaces.error = payload.error;
      if (!payload.data) {
        return;
      }
      state.spaces.data = payload.data.spaces;
    },
    [UPDATE_ADDED_SPACE](state, payload) {
      state.spaces.data.push(payload);
    },
    [UPDATE_CHANGED_SPACE](state, payload) {
      state.spaces.data = state.spaces.data.map((space) => {
        if (space.uuid !== payload.id) return space;

        return {
          ...space,
          name: payload.name,
          roles: payload.roles,
          public: payload.public,
        };
      });
    },
    [UPDATE_REMOVED_SPACE](state, spaceId) {
      state.spaces.data = state.spaces.data.filter((item) => item.uuid !== spaceId);
    },
    [TOGGLE_TUNNEL_CONNECTION_MODAL](state, payload) {
      state.tunnelDisconnected = payload && payload.status ? payload.status : false;
    },
    [RESET_TUNNEL_CONNECTION_CHECKING](state) {
      state.lifecycle.data.tunnelStatus = tunnelConnectionStatuses.notAvailable;
    },
  },
  actions: {
    [FETCH_LIFECYCLE]({ dispatch, commit, state }) {
      const currentLifecycleStatus = state.lifecycle.data.status;
      const currentTunnelStatus = state.lifecycle.data.tunnelStatus;
      return dispatch(REQUEST_API, {
        rule: 'dashboard/lifecycle',
        type: UPDATE_LIFECYCLE,
      }).then(() => {
        if (currentLifecycleStatus !== 'done' && state.lifecycle.data.status === 'done') {
          commit(RESET_DEVICES_MERGED_DATA_BY_ID);
        }
        if (currentTunnelStatus
            && currentTunnelStatus !== state.lifecycle.data.tunnelStatus
            && state.lifecycle.data.tunnelStatus === tunnelConnectionStatuses.disconnected) {
          commit(TOGGLE_TUNNEL_CONNECTION_MODAL, { status: true });
        }
      });
    },
    [FETCH_DISCOVERY_DATA]({ dispatch }, payload) {
      if (!payload || !payload.module) {
        return false;
      }
      return dispatch(REQUEST_API, {
        rule: `dashboard/adapter_data/${payload.module}`,
        payload,
      });
    },
    [FETCH_DASHBOARD_SPACES]({ dispatch }, payload) {
      return dispatch(REQUEST_API, {
        rule: 'dashboard',
        type: UPDATE_DASHBOARD_SPACES,
        payload,
      });
    },
    [SAVE_REORDERED_PANELS]({ dispatch }, payload) {
      return dispatch(REQUEST_API, {
        rule: `dashboard/reorder/${payload.spaceId}`,
        method: 'POST',
        data: payload,
      });
    },
    [SAVE_DASHBOARD_SPACE]({ dispatch, commit }, data) {
      return dispatch(REQUEST_API, {
        rule: 'dashboard',
        method: 'POST',
        data,
      }).then((response) => {
        if (response.status === 200 && response.data) {
          commit(UPDATE_ADDED_SPACE, {
            ...data,
            uuid: response.data,
            type: 'custom',
          });
        }
        return response.data;
      });
    },
    [CHANGE_DASHBOARD_SPACE]({ dispatch, commit }, payload) {
      return dispatch(REQUEST_API, {
        rule: `dashboard/${payload.id}`,
        method: 'PUT',
        data: {
          name: payload.name,
          roles: payload.roles,
          public: payload.public,
        },
      }).then((response) => {
        if (response.status === 200) {
          commit(UPDATE_CHANGED_SPACE, payload);
        }
      });
    },
    [REMOVE_DASHBOARD_SPACE]({ dispatch, commit }, spaceId) {
      return dispatch(REQUEST_API, {
        rule: `dashboard/${spaceId}`,
        method: 'DELETE',
      }).then((response) => {
        if (response.status === 200) {
          commit(UPDATE_REMOVED_SPACE, spaceId);
          dispatch(FETCH_DASHBOARD_SPACES);
        }
      });
    },
    [SAVE_DASHBOARD_PANEL]({ dispatch }, payload) {
      return dispatch(REQUEST_API, {
        rule: `dashboard/charts/${payload.space}`,
        method: 'PUT',
        data: payload.data,
      });
    },
    [CHANGE_DASHBOARD_PANEL]({ dispatch }, payload) {
      return dispatch(REQUEST_API, {
        rule: `dashboard/charts/${payload.panelId}`,
        method: 'POST',
        data: _pick(payload.data, ['name', 'config', 'metric', 'view']),
      });
    },
    [REMOVE_DASHBOARD_PANEL]({ dispatch }, payload) {
      if (!payload.panelId) {
        return false;
      }
      return dispatch(REQUEST_API, {
        rule: `dashboard/charts/${payload.panelId}`,
        method: 'DELETE',
        data: payload,
      });
    },
    [FETCH_CHART_CSV]({ dispatch }, { uuid, name, historical }) {
      let rule = `dashboard/charts/${uuid}/csv`;
      if (historical) {
        const encodedDate = encodeURI(historical);
        rule = `${rule}?date_to=${encodedDate} 23:59:59&date_from=${encodedDate}`;
      }
      return dispatch(REQUEST_API, {
        rule,
      }).then((response) => {
        downloadFile('csv', response, name);
      });
    },
    [MOVE_PANEL]({ dispatch }, payload) {
      // no need to move panel to the same space
      return dispatch(REQUEST_API, {
        rule: `dashboard/charts/move/${payload.uuid}`,
        method: 'PUT',
        data: { destinationSpace: payload.space },
      });
    },
    [COPY_PANEL]({ dispatch }, { chart, space }) {
      const {
        metric, name, view, config,
      } = chart;
      return dispatch(SAVE_DASHBOARD_PANEL, {
        data: {
          metric,
          name,
          view,
          config,
          linked_dashboard: null,
        },
        space,
      });
    },
  },
  getters: {
    [GET_SPACE_BY_ID]: (state) => (spaceId) => state.spaces.data.find((s) => s.uuid === spaceId) || {},
  },
};
