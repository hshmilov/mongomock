import Vue from 'vue'
import Vuex from 'vuex'

import {
  REQUEST_API, requestApi,
  FETCH_DATA_CONTENT, fetchDataContent,
  FETCH_DATA_CONTENT_CSV, fetchDataContentCSV,
  FETCH_DATA_COUNT, fetchDataCount,
  FETCH_DATA_VIEWS, fetchDataViews,
  SAVE_DATA_VIEW, saveDataView,
  SAVE_VIEW, saveView,
  FETCH_DATA_FIELDS, fetchDataFields,
  FETCH_DATA_HYPERLINKS, fetchDataHyperlinks,
  START_RESEARCH_PHASE, startResearch,
  FETCH_DATA_LABELS, fetchDataLabels,
  ADD_DATA_LABELS, addDataLabels,
  REMOVE_DATA_LABELS, removeDataLabels,
  DISABLE_DATA, disableData,
  DELETE_DATA, deleteData,
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
  SAVE_CUSTOM_DATA, saveCustomData
} from './actions'
import {
  TOGGLE_SIDEBAR, toggleSidebar,
  UPDATE_DATA, updateData,
  UPDATE_LANGUAGE , updateLanguage,
  UPDATE_BRANCH, updateBranch,
  UPDATE_WINDOW_WIDTH, updateWindowWidth,
  UPDATE_DATA_CONTENT, updateDataContent,
  UPDATE_DATA_COUNT, updateDataCount,
  UPDATE_DATA_COUNT_QUICK, updateDataCountQuick,
  UPDATE_DATA_VIEW, updateDataView,
  UPDATE_DATA_VIEWS, updateDataViews,
  ADD_DATA_VIEW, addDataView,
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
  REMOVE_TOASTER, removeToaster
} from './mutations'
import {
  GET_DATA_FIELDS_BY_PLUGIN, getDataFieldsByPlugin,
  GET_DATA_SCHEMA_BY_NAME, getDataSchemaByName,
  GET_DATA_FIELD_LIST_SPREAD, getDataFieldListSpread,
  GET_DATA_BY_ID, getDataByID,
  SINGLE_ADAPTER, singleAdapter,
  AUTO_QUERY, autoQuery,
  IS_EXPIRED, isExpired
} from './getters'

import { adapters } from './modules/adapters'
import { auth } from './modules/auth'
import { constants } from './modules/constants'
import { dashboard } from './modules/dashboard'
import { devices } from './modules/devices'
import { enforcements } from './modules/enforcements'
import { notifications } from './modules/notifications'
import { onboarding } from './modules/onboarding'
import { reports } from './modules/reports'
import { settings } from './modules/settings'
import { tasks } from './modules/tasks'
import { users } from './modules/users'

Vue.use(Vuex)
export default new Vuex.Store({
  state: {
    /*
        General controls that the system uses throughout pages
     */
    interaction: {
      language: 'en',
      branch: '',
      collapseSidebar: true,
      windowWidth: 0
    },
    configuration: { fetching: false, data: null, error: '' },
    staticConfiguration: { medicalConfig: ENV.medical },
    expired: { fetching: false, data: false, error: '' },
    toast: { message: '', timeout: 3000 }
  },
  getters: {
    [GET_DATA_FIELDS_BY_PLUGIN]: getDataFieldsByPlugin,
    [GET_DATA_SCHEMA_BY_NAME]: getDataSchemaByName,
    [GET_DATA_FIELD_LIST_SPREAD]: getDataFieldListSpread,
    [GET_DATA_BY_ID]: getDataByID,
    [SINGLE_ADAPTER]: singleAdapter,
    [AUTO_QUERY]: autoQuery,
    [IS_EXPIRED]: isExpired
  },
  mutations: {
    [TOGGLE_SIDEBAR]: toggleSidebar,
    [UPDATE_DATA]: updateData,
    [UPDATE_LANGUAGE]: updateLanguage,
    [UPDATE_BRANCH]: updateBranch,
    [UPDATE_WINDOW_WIDTH]: updateWindowWidth,
    [UPDATE_DATA_CONTENT]: updateDataContent,
    [UPDATE_DATA_COUNT]: updateDataCount,
    [UPDATE_DATA_COUNT_QUICK]: updateDataCountQuick,
    [UPDATE_DATA_VIEW]: updateDataView,
    [UPDATE_DATA_VIEWS]: updateDataViews,
    [ADD_DATA_VIEW]: addDataView,
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
    [REMOVE_TOASTER]: removeToaster
  },
  actions: {
    [REQUEST_API]: requestApi,
    [FETCH_DATA_CONTENT]: fetchDataContent,
    [FETCH_DATA_CONTENT_CSV]: fetchDataContentCSV,
    [FETCH_DATA_COUNT]: fetchDataCount,
    [FETCH_DATA_VIEWS]: fetchDataViews,
    [SAVE_DATA_VIEW]: saveDataView,
    [SAVE_VIEW]: saveView,
    [FETCH_DATA_FIELDS]: fetchDataFields,
    [FETCH_DATA_HYPERLINKS]: fetchDataHyperlinks,
    [START_RESEARCH_PHASE]: startResearch,
    [FETCH_DATA_LABELS]: fetchDataLabels,
    [ADD_DATA_LABELS]: addDataLabels,
    [REMOVE_DATA_LABELS]: removeDataLabels,
    [DISABLE_DATA]: disableData,
    [DELETE_DATA]: deleteData,
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
    [SAVE_CUSTOM_DATA]: saveCustomData
  },
  modules: {
    /*
        System's controls resource, relevant for each component.
        Module stores controls and manages the way of obtaining it.
     */
    adapters,
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
    users
  }
})