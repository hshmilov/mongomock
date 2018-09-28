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
	REMOVE_DATA_VIEW, removeDataView,
	FETCH_DATA_FIELDS, fetchDataFields,
    START_RESEARCH_PHASE, startResearch,
	FETCH_DATA_LABELS, fetchDataLabels,
	ADD_DATA_LABELS, addDataLabels,
	REMOVE_DATA_LABELS, removeDataLabels,
	DISABLE_DATA, disableData,
	DELETE_DATA, deleteData,
	FETCH_DATA_BY_ID, fetchDataByID,
	RUN_ACTION, runAction,
    STOP_RESEARCH_PHASE, stopResearch,
	FETCH_SYSTEM_CONFIG, fetchSystemConfig
} from './actions'
import {
	TOGGLE_SIDEBAR, toggleSidebar,
	UPDATE_DATA_CONTENT, updateDataContent,
	UPDATE_DATA_COUNT, updateDataCount,
	UPDATE_DATA_VIEW, updateDataView,
	CLEAR_DATA_CONTENT, clearDataContent,
	UPDATE_DATA_VIEWS, updateDataViews,
	ADD_DATA_VIEW, addDataView,
	UPDATE_REMOVED_DATA_VIEW, updateRemovedDataView,
	UPDATE_DATA_FIELDS, updateDataFields,
	UPDATE_DATA_LABELS, updateDataLabels,
	UPDATE_ADDED_DATA_LABELS, updateAddedDataLabels,
	UPDATE_REMOVED_DATA_LABELS, updateRemovedDataLabels,
	UPDATE_DATA_BY_ID, updateDataByID,
    UPDATE_SYSTEM_CONFIG, updateSystemConfig
} from './mutations'
import {
	GET_DATA_FIELD_BY_PLUGIN, getDataFieldsByPlugin,
	GET_DATA_FIELD_LIST_SPREAD, getDataFieldListSpread,
	GET_DATA_BY_ID, getDataByID,
	SINGLE_ADAPTER, singleAdapter
} from './getters'
import { devices } from './modules/devices'
import { users } from './modules/users'
import { adapter } from './modules/adapter'
import { alert } from './modules/alert'
import { notifications } from './modules/notifications'
import { auth } from './modules/auth'
import { constants } from './modules/constants'
import { dashboard } from './modules/dashboard'
import { report } from './modules/report'
import { configurable } from './modules/configurable'
import { onboarding } from './modules/onboarding'

Vue.use(Vuex)
export default new Vuex.Store({
    state: {
        /*
            General controls that the system uses throughout pages
         */
        interaction: {
            collapseSidebar: true
        },
		configuration: { fetching: false, data: null, error: '' }
    },
	getters: {
		[ GET_DATA_FIELD_BY_PLUGIN ]: getDataFieldsByPlugin,
		[ GET_DATA_FIELD_LIST_SPREAD ]: getDataFieldListSpread,
		[ GET_DATA_BY_ID ]: getDataByID,
		[ SINGLE_ADAPTER ]: singleAdapter
	},
    mutations: {
        [ TOGGLE_SIDEBAR ]: toggleSidebar,
        [ UPDATE_DATA_CONTENT ]: updateDataContent,
		[ UPDATE_DATA_COUNT ]: updateDataCount,
		[ UPDATE_DATA_VIEW ]: updateDataView,
		[ CLEAR_DATA_CONTENT ]: clearDataContent,
		[ UPDATE_DATA_VIEWS ]: updateDataViews,
		[ ADD_DATA_VIEW ]: addDataView,
		[ UPDATE_REMOVED_DATA_VIEW ]: updateRemovedDataView,
		[ UPDATE_DATA_FIELDS ]: updateDataFields,
		[ UPDATE_DATA_LABELS ]: updateDataLabels,
		[ UPDATE_ADDED_DATA_LABELS ]: updateAddedDataLabels,
		[ UPDATE_REMOVED_DATA_LABELS ]: updateRemovedDataLabels,
		[ UPDATE_DATA_BY_ID ]: updateDataByID,
		[ UPDATE_SYSTEM_CONFIG ]: updateSystemConfig
    },
    actions: {
        [ REQUEST_API ]: requestApi,
        [ FETCH_DATA_CONTENT ]: fetchDataContent,
		[ FETCH_DATA_CONTENT_CSV ]: fetchDataContentCSV,
		[ FETCH_DATA_COUNT ]: fetchDataCount,
		[ FETCH_DATA_VIEWS ]: fetchDataViews,
		[ SAVE_DATA_VIEW ]: saveDataView,
		[ SAVE_VIEW ]: saveView,
		[ REMOVE_DATA_VIEW ]: removeDataView,
		[ FETCH_DATA_FIELDS ]: fetchDataFields,
		[ START_RESEARCH_PHASE ]: startResearch,
		[ FETCH_DATA_LABELS ]: fetchDataLabels,
		[ ADD_DATA_LABELS ]: addDataLabels,
		[ REMOVE_DATA_LABELS ]: removeDataLabels,
		[ DISABLE_DATA ]: disableData,
		[ DELETE_DATA ]: deleteData,
		[ FETCH_DATA_BY_ID ]: fetchDataByID,
		[ RUN_ACTION ]: runAction,
        [ STOP_RESEARCH_PHASE ]: stopResearch,
		[ FETCH_SYSTEM_CONFIG ]: fetchSystemConfig
    },
    modules: {
        /*
            System's controls resource, relevant for each component.
            Module stores controls and manages the way of obtaining it.
         */
        devices,
		users,
		adapter,
		alert,
        notifications,
        auth,
        constants,
        dashboard,
		report,
		configurable,
		onboarding
    }

})