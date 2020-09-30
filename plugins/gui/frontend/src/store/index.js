import Vue from 'vue';
import Vuex from 'vuex';

import {
  REQUEST_API, requestApi,
  FETCH_DATA_CONTENT, fetchDataContent,
  FETCH_DATA_CONTENT_CSV, fetchDataContentCSV,
  FETCH_DATA_COUNT, fetchDataCount,
  SAVE_DATA_VIEW, saveDataView,
  SAVE_VIEW, saveView,
  PUBLISH_VIEW, publishView,
  FETCH_DATA_FIELDS, fetchDataFields,
  LAZY_FETCH_DATA_FIELDS, lazyFetchDataFields,
  FETCH_DATA_HYPERLINKS, fetchDataHyperlinks,
  START_RESEARCH_PHASE, startResearch,
  FETCH_DATA_LABELS, fetchDataLabels,
  ADD_DATA_LABELS, addDataLabels,
  REMOVE_DATA_LABELS, removeDataLabels,
  DELETE_DATA, deleteData,
  DELETE_VIEW_DATA, deleteViewData,
  LINK_DATA, linkData,
  UNLINK_DATA, unlinkData,
  ENFORCE_DATA, enforceData,
  FETCH_DATA_CURRENT, fetchDataCurrent,
  FETCH_DATA_CURRENT_TASKS, fetchDataCurrentTasks,
  SAVE_DATA_NOTE, saveDataNote,
  REMOVE_DATA_NOTE, removeDataNote,
  RUN_ACTION, runAction,
  STOP_RESEARCH_PHASE, stopResearch,
  FETCH_SYSTEM_CONFIG, fetchSystemConfig,
  FETCH_SYSTEM_EXPIRED, fetchSystemExpired,
  SAVE_CUSTOM_DATA, saveCustomData,
  GET_ENVIRONMENT_NAME, getEnvironmentName,
  GET_TUNNEL_STATUS, getTunnelStatus,
  SAVE_TUNNEL_EMAILS_LIST, saveTunnelEmailsList,
  GET_TUNNEL_EMAILS_LIST, getTunnelEmailsList,
  GET_TUNNEL_PROXY_SETTINGS, getTunnelProxySettings,
  SAVE_TUNNEL_PROXY_SETTINGS, saveTunnelProxySettings,
  SAVE_SYSTEM_DEFAULT_COLUMNS, saveSystemDefaultColumns,
  FETCH_QUERY_INVALID_REFERENCES, fetchInvalidReferences,
} from './actions';
import {
  TOGGLE_SIDEBAR, toggleSidebar,
  UPDATE_DATA, updateData,
  UPDATE_LANGUAGE, updateLanguage,
  UPDATE_BRANCH, updateBranch,
  UPDATE_DATA_CONTENT, updateDataContent,
  UPDATE_DATA_COUNT, updateDataCount,
  UPDATE_DATA_COUNT_QUICK, updateDataCountQuick,
  UPDATE_DATA_VIEW, updateDataView,
  UPDATE_DATA_VIEW_FILTER, updateDataViewFilter,
  CLEAR_DATA_VIEW_FILTERS, clearDataViewFilter,
  ADD_DATA_VIEW, addDataView,
  CHANGE_DATA_VIEW, changeDataView,
  UPDATE_REMOVED_DATA_VIEW, updateRemovedDataView,
  UPDATE_DATA_FIELDS, updateDataFields,
  UPDATE_DATA_HYPERLINKS, updateDataHyperlinks,
  UPDATE_DATA_LABELS, updateDataLabels,
  UPDATE_ADDED_DATA_LABELS, updateAddedDataLabels,
  UPDATE_REMOVED_DATA_LABELS, updateRemovedDataLabels,
  SELECT_DATA_CURRENT, selectDataCurrent,
  UPDATE_DATA_CURRENT, updateDataCurrent,
  UPDATE_SAVED_DATA_NOTE, updateSavedDataNote,
  UPDATE_REMOVED_DATA_NOTE, updateRemovedDataNote,
  UPDATE_SYSTEM_CONFIG, updateSystemConfig,
  UPDATE_SYSTEM_EXPIRED, updateSystemExpired,
  UPDATE_CUSTOM_DATA, updateCustomData,
  SHOW_TOASTER_MESSAGE, showToasterMessage,
  UPDATE_FOOTER_MESSAGE, updateFooterMessage,
  REMOVE_TOASTER, removeToaster,
  UPDATE_SYSTEM_DEFAULT_COLUMNS, updateSystemDefaultColumns,
  UPDATE_QUERY_INVALID_REFERENCES, updateQueryInvalidReferences,
  UPDATE_QUERY_ERROR, updateQueryError
} from './mutations';
import {
  GET_MODULE_SCHEMA, getModuleSchema,
  GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL, getModuleSchemaWithConnectionLabel,
  GET_DATA_SCHEMA_LIST, getDataSchemaList,
  GET_DATA_SCHEMA_BY_NAME, getDataSchemaByName,
  AUTO_QUERY, autoQuery,
  EXACT_SEARCH, exactSearch,
  REQUIRE_CONNECTION_LABEL, requireConnectionLabel,
  IS_EXPIRED, isExpired,
  DATE_FORMAT, dateFormat,
  GET_CONNECTION_LABEL, getConnectionLabel,
  getSavedQueryById,
  configuredAdaptersFields,
  GET_FOOTER_MESSAGE, getFooterMessage,
  FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES, fillUserFieldsGroupsFromTemplates,
  GET_SYSTEM_COLUMNS, getSystemColumns,
  GET_SAVED_QUERY_BY_NAME, getSavedQueryByName,
} from './getters';

import { adapters } from './modules/adapters';
import audit from './modules/audit';
import { auth } from './modules/auth';
import { constants } from './modules/constants';
import { dashboard } from './modules/dashboard';
import { devices } from './modules/devices';
import { enforcements } from './modules/enforcements';
import { notifications } from './modules/notifications';
import { onboarding } from './modules/onboarding';
import { reports } from './modules/reports';
import { settings } from './modules/settings';
import { tasks } from './modules/tasks';
import { users } from './modules/users';
import { compliance } from './modules/compliance';
import { labels } from './modules/labels';

Vue.use(Vuex);
export default new Vuex.Store({
  state: {
    /*
        General controls that the system uses throughout pages
     */
    interaction: {
      language: 'en',
      branch: '',
      collapseSidebar: true,
      windowWidth: 0,
    },
    configuration: {
      fetching: false,
      data: {
        defaults: {
          system_columns: { },
        },
      },
      error: '',
    },
    expired: { fetching: false, data: false, error: '' },
    toast: { message: '', timeout: 3000 },
    footer: { message: '' },
  },
  getters: {
    [GET_MODULE_SCHEMA]: getModuleSchema,
    [GET_DATA_SCHEMA_LIST]: getDataSchemaList,
    [GET_DATA_SCHEMA_BY_NAME]: getDataSchemaByName,
    [AUTO_QUERY]: autoQuery,
    [EXACT_SEARCH]: exactSearch,
    [REQUIRE_CONNECTION_LABEL]: requireConnectionLabel,
    [IS_EXPIRED]: isExpired,
    isExpired,
    [DATE_FORMAT]: dateFormat,
    [GET_CONNECTION_LABEL]: getConnectionLabel,
    [GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL]: getModuleSchemaWithConnectionLabel,
    getSavedQueryById,
    configuredAdaptersFields,
    [GET_FOOTER_MESSAGE]: getFooterMessage,
    [FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES]: fillUserFieldsGroupsFromTemplates,
    [GET_SYSTEM_COLUMNS]: getSystemColumns,
    [GET_SAVED_QUERY_BY_NAME]: getSavedQueryByName,
  },
  mutations: {
    [TOGGLE_SIDEBAR]: toggleSidebar,
    [UPDATE_DATA]: updateData,
    [UPDATE_LANGUAGE]: updateLanguage,
    [UPDATE_BRANCH]: updateBranch,
    [UPDATE_DATA_CONTENT]: updateDataContent,
    [UPDATE_DATA_COUNT]: updateDataCount,
    [UPDATE_DATA_COUNT_QUICK]: updateDataCountQuick,
    [UPDATE_DATA_VIEW]: updateDataView,
    [UPDATE_DATA_VIEW_FILTER]: updateDataViewFilter,
    [CLEAR_DATA_VIEW_FILTERS]: clearDataViewFilter,
    [ADD_DATA_VIEW]: addDataView,
    [CHANGE_DATA_VIEW]: changeDataView,
    [UPDATE_REMOVED_DATA_VIEW]: updateRemovedDataView,
    [UPDATE_DATA_FIELDS]: updateDataFields,
    [UPDATE_DATA_HYPERLINKS]: updateDataHyperlinks,
    [UPDATE_DATA_LABELS]: updateDataLabels,
    [UPDATE_ADDED_DATA_LABELS]: updateAddedDataLabels,
    [UPDATE_REMOVED_DATA_LABELS]: updateRemovedDataLabels,
    [SELECT_DATA_CURRENT]: selectDataCurrent,
    [UPDATE_DATA_CURRENT]: updateDataCurrent,
    [UPDATE_SAVED_DATA_NOTE]: updateSavedDataNote,
    [UPDATE_REMOVED_DATA_NOTE]: updateRemovedDataNote,
    [UPDATE_SYSTEM_CONFIG]: updateSystemConfig,
    [UPDATE_SYSTEM_EXPIRED]: updateSystemExpired,
    [UPDATE_CUSTOM_DATA]: updateCustomData,
    [SHOW_TOASTER_MESSAGE]: showToasterMessage,
    [REMOVE_TOASTER]: removeToaster,
    [UPDATE_FOOTER_MESSAGE]: updateFooterMessage,
    [UPDATE_SYSTEM_DEFAULT_COLUMNS]: updateSystemDefaultColumns,
    [UPDATE_QUERY_INVALID_REFERENCES]: updateQueryInvalidReferences,
    [UPDATE_QUERY_ERROR]: updateQueryError,
  },
  actions: {
    [REQUEST_API]: requestApi,
    [FETCH_DATA_CONTENT]: fetchDataContent,
    [FETCH_DATA_CONTENT_CSV]: fetchDataContentCSV,
    [FETCH_DATA_COUNT]: fetchDataCount,
    [SAVE_DATA_VIEW]: saveDataView,
    [SAVE_VIEW]: saveView,
    [PUBLISH_VIEW]: publishView,
    [FETCH_DATA_FIELDS]: fetchDataFields,
    [LAZY_FETCH_DATA_FIELDS]: lazyFetchDataFields,
    [FETCH_DATA_HYPERLINKS]: fetchDataHyperlinks,
    [START_RESEARCH_PHASE]: startResearch,
    [FETCH_DATA_LABELS]: fetchDataLabels,
    [ADD_DATA_LABELS]: addDataLabels,
    [REMOVE_DATA_LABELS]: removeDataLabels,
    [DELETE_DATA]: deleteData,
    [DELETE_VIEW_DATA]: deleteViewData,
    [LINK_DATA]: linkData,
    [UNLINK_DATA]: unlinkData,
    [ENFORCE_DATA]: enforceData,
    [FETCH_DATA_CURRENT]: fetchDataCurrent,
    [FETCH_DATA_CURRENT_TASKS]: fetchDataCurrentTasks,
    [SAVE_DATA_NOTE]: saveDataNote,
    [REMOVE_DATA_NOTE]: removeDataNote,
    [RUN_ACTION]: runAction,
    [STOP_RESEARCH_PHASE]: stopResearch,
    [FETCH_SYSTEM_CONFIG]: fetchSystemConfig,
    [FETCH_SYSTEM_EXPIRED]: fetchSystemExpired,
    [SAVE_CUSTOM_DATA]: saveCustomData,
    [GET_ENVIRONMENT_NAME]: getEnvironmentName,
    [GET_TUNNEL_STATUS]: getTunnelStatus,
    [SAVE_TUNNEL_EMAILS_LIST]: saveTunnelEmailsList,
    [GET_TUNNEL_EMAILS_LIST]: getTunnelEmailsList,
    [GET_TUNNEL_PROXY_SETTINGS]: getTunnelProxySettings,
    [SAVE_TUNNEL_PROXY_SETTINGS]: saveTunnelProxySettings,
    [SAVE_SYSTEM_DEFAULT_COLUMNS]: saveSystemDefaultColumns,
    [FETCH_QUERY_INVALID_REFERENCES]: fetchInvalidReferences,
  },
  modules: {
    /*
        System's controls resource, relevant for each component.
        Module stores controls and manages the way of obtaining it.
     */
    adapters,
    audit,
    auth,
    constants,
    dashboard,
    devices,
    enforcements,
    notifications,
    onboarding,
    reports,
    settings,
    tasks,
    users,
    compliance,
    labels,
  },
});
