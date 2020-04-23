/* eslint-disable no-param-reassign */
import _get from 'lodash/get';
import { REQUEST_API } from '../actions';

export const IN_TRIAL = 'IN_TRIAL';
export const SHOULD_SHOW_CLOUD_COMPLIANCE = 'SHOULD_SHOW_CLOUD_COMPLIANCE';

export const SAVE_PLUGIN_CONFIG = 'SAVE_PLUGIN_CONFIG';
export const LOAD_PLUGIN_CONFIG = 'LOAD_PLUGIN_CONFIG';
export const CHANGE_PLUGIN_CONFIG = 'CHANGE_PLUGIN_CONFIG';
export const FETCH_FETURE_FLAGS = 'FETCH_FETURE_FLAGS';

export const FETCH_MAINTENANCE_CONFIG = 'FETCH_MAINTENANCE_CONFIG';
export const UPDATE_MAINTENANCE_CONFIG = 'UPDATE_MAINTENANCE_CONFIG';
export const SAVE_MAINTENANCE_CONFIG = 'SAVE_MAINTENANCE_CONFIG';
export const START_MAINTENANCE_CONFIG = 'START_MAINTENANCE_CONFIG';
export const STOP_MAINTENANCE_CONFIG = 'STOP_MAINTENANCE_CONFIG';

export const settings = {
  state: {
    configurable: {},
    advanced: {
      maintenance: {
        provision: true,
        analytics: true,
        troubleshooting: true,
        timeout: null,
      },
    },
  },
  getters: {
    featureFlags: (state) => {
      if (!state.configurable.gui || !state.configurable.gui.FeatureFlags) {
        return null;
      }
      return state.configurable.gui.FeatureFlags.config;
    },
    [IN_TRIAL]: (state) => {
      if (!state.configurable.gui || !state.configurable.gui.FeatureFlags) {
        return true;
      }
      const featureFlags = state.configurable.gui.FeatureFlags.config;
      if (!_get(featureFlags, 'trial_end')) return null;

      const expirationDate = new Date(featureFlags.trial_end);
      expirationDate.setMinutes(expirationDate.getMinutes() - expirationDate.getTimezoneOffset());
      const trialDaysRemaining = Math.ceil((expirationDate - new Date()) / 1000 / 60 / 60 / 24);
      return trialDaysRemaining !== null;
    },
    [SHOULD_SHOW_CLOUD_COMPLIANCE]: (state, getters) => {
      const cloudComplianceSettings = _get(getters, 'featureFlags.cloud_compliance', {});
      // If we are in trial, or if the cloud compliance feature has been enabled, run this.
      const isCloudComplianceEnabled = cloudComplianceSettings.cis_enabled;
      const isCloudComplianceVisible = cloudComplianceSettings.enabled;
      return isCloudComplianceVisible && (getters.IN_TRIAL || isCloudComplianceEnabled);
    },
  },
  mutations: {
    [CHANGE_PLUGIN_CONFIG](state, payload) {
      if (!state.configurable[payload.pluginId]) {
        state.configurable[payload.pluginId] = {};
      }
      if (!state.configurable[payload.pluginId][payload.configName]) {
        state.configurable[payload.pluginId][payload.configName] = {};
      }
      state.configurable = {
        ...state.configurable,
        [payload.pluginId]: {
          ...state.configurable[payload.pluginId],
          [payload.configName]: {
            fetching: payload.fetching,
            error: payload.error,
            config: payload.data ? payload.data.config
              : state.configurable[payload.pluginId][payload.configName].config,
            schema: payload.data ? payload.data.schema
              : state.configurable[payload.pluginId][payload.configName].schema,
          },
        },
      };
    },
    [UPDATE_MAINTENANCE_CONFIG](state, payload) {
      if (payload.data) {
        state.advanced.maintenance = {
          ...state.advanced.maintenance, ...payload.data,
        };
      }
    },
  },
  actions: {
    [FETCH_FETURE_FLAGS]({ dispatch }) {
      const guiPluginFeatureFlagsConfig = {
        pluginId: 'gui',
        configName: 'FeatureFlags',
      };
      dispatch(LOAD_PLUGIN_CONFIG, guiPluginFeatureFlagsConfig);
    },
    [SAVE_PLUGIN_CONFIG]({ dispatch, commit }, payload) {
      /*
          Call API to save given config to adapters by the given adapters unique name
       */
      if (!payload || !payload.pluginId || !payload.configName) {
        return null;
      }
      const rulePrefix = payload.prefix || 'settings/plugins';
      const rule = `${rulePrefix}/${payload.pluginId}/${payload.configName}`;
      return dispatch(REQUEST_API, {
        rule,
        method: 'POST',
        data: payload.config,
      }).then((response) => {
        if (response.status === 200) {
          commit(CHANGE_PLUGIN_CONFIG, {
            pluginId: payload.pluginId,
            configName: payload.configName,
            config: payload.config,
          });
        }
        return response;
      });
    },
    [LOAD_PLUGIN_CONFIG]({ dispatch }, payload) {
      /*
          Call API to save given config to adapters by the given adapters unique name
       */
      if (!payload || !payload.pluginId || !payload.configName) return null;

      const rule = `settings/plugins/${payload.pluginId}/${payload.configName}`;
      return dispatch(REQUEST_API, {
        rule,
        type: CHANGE_PLUGIN_CONFIG,
        payload,
      });
    },
    [FETCH_MAINTENANCE_CONFIG]({ dispatch }) {
      return dispatch(REQUEST_API, {
        rule: 'settings/maintenance',
        type: UPDATE_MAINTENANCE_CONFIG,
      });
    },
    [SAVE_MAINTENANCE_CONFIG]({ dispatch, commit }, payload) {
      if (payload.provision) {
        payload = {
          ...payload,
          analytics: true,
          troubleshooting: true,
          timeout: null,
        };
      }
      return dispatch(REQUEST_API, {
        rule: 'settings/maintenance',
        method: 'POST',
        data: payload,
      }).then((response) => {
        if (response.status === 200) {
          commit(UPDATE_MAINTENANCE_CONFIG, {
            data: payload,
          });
        }
      });
    },
    [START_MAINTENANCE_CONFIG]({ dispatch, commit }, payload) {
      return dispatch(REQUEST_API, {
        rule: 'settings/maintenance',
        method: 'PUT',
        data: payload,
      }).then((response) => {
        if (response.status === 200 && response.data) {
          commit(UPDATE_MAINTENANCE_CONFIG, {
            data: response.data,
          });
        }
      });
    },
    [STOP_MAINTENANCE_CONFIG]({ dispatch, commit }) {
      return dispatch(REQUEST_API, {
        rule: 'settings/maintenance',
        method: 'DELETE',
      }).then((response) => {
        if (response.status === 200) {
          commit(UPDATE_MAINTENANCE_CONFIG, {
            data: {
              timeout: null,
            },
          });
        }
      });
    },
  },
};
