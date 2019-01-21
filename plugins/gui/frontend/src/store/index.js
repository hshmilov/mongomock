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
	FETCH_DATA_HYPERLINKS, fetchDataHyperlinks,
    START_RESEARCH_PHASE, startResearch,
	FETCH_DATA_LABELS, fetchDataLabels,
	ADD_DATA_LABELS, addDataLabels,
	REMOVE_DATA_LABELS, removeDataLabels,
	DISABLE_DATA, disableData,
	DELETE_DATA, deleteData,
	LINK_DATA, linkData,
	UNLINK_DATA, unlinkData,
	FETCH_DATA_BY_ID, fetchDataByID,
	SAVE_DATA_NOTE, saveDataNote,
	REMOVE_DATA_NOTE, removeDataNote,
	RUN_ACTION, runAction,
    STOP_RESEARCH_PHASE, stopResearch,
	FETCH_SYSTEM_CONFIG, fetchSystemConfig,
    SAVE_CUSTOM_DATA, saveCustomData
} from './actions'
import {
	TOGGLE_SIDEBAR, toggleSidebar,
    UPDATE_WINDOW_WIDTH, updateWindowWidth,
	UPDATE_DATA_CONTENT, updateDataContent,
	UPDATE_DATA_COUNT, updateDataCount,
	UPDATE_DATA_VIEW, updateDataView,
	UPDATE_DATA_VIEWS, updateDataViews,
	ADD_DATA_VIEW, addDataView,
	UPDATE_REMOVED_DATA_VIEW, updateRemovedDataView,
	UPDATE_DATA_FIELDS, updateDataFields,
	UPDATE_DATA_HYPERLINKS, updateDataHyperlinks,
	UPDATE_DATA_LABELS, updateDataLabels,
	UPDATE_ADDED_DATA_LABELS, updateAddedDataLabels,
	UPDATE_REMOVED_DATA_LABELS, updateRemovedDataLabels,
	UPDATE_DATA_BY_ID, updateDataByID,
	UPDATE_SAVED_DATA_NOTE, updateSavedDataNote,
	UPDATE_REMOVED_DATA_NOTE, updateRemovedDataNote,
    UPDATE_SYSTEM_CONFIG, updateSystemConfig
} from './mutations'
import {
	GET_DATA_FIELDS_BY_PLUGIN, getDataFieldsByPlugin,
    GET_DATA_SCHEMA_BY_NAME, getDataSchemaByName,
	GET_DATA_FIELD_LIST_SPREAD, getDataFieldListSpread,
	GET_DATA_BY_ID, getDataByID,
	SINGLE_ADAPTER, singleAdapter
} from './getters'
import { devices } from './modules/devices'
import { users } from './modules/users'
import { explorer } from './modules/explorer'
import { adapters } from './modules/adapters'
import { alerts } from './modules/alerts'
import { notifications } from './modules/notifications'
import { auth } from './modules/auth'
import { constants } from './modules/constants'
import { dashboard } from './modules/dashboard'
import { reports } from './modules/reports'
import { settings } from './modules/settings'
import { onboarding } from './modules/onboarding'

Vue.use(Vuex)
export default new Vuex.Store({
    state: {
        /*
            General controls that the system uses throughout pages
         */
        interaction: {
            collapseSidebar: true,
            windowWidth: 0
        },
		configuration: { fetching: false, data: null, error: '' }
    },
	getters: {
        [ GET_DATA_FIELDS_BY_PLUGIN ]: getDataFieldsByPlugin,
        [ GET_DATA_SCHEMA_BY_NAME ]: getDataSchemaByName,
        [ GET_DATA_FIELD_LIST_SPREAD ]: getDataFieldListSpread,
        [ GET_DATA_BY_ID ]: getDataByID,
        [ SINGLE_ADAPTER ]: singleAdapter
	},
    mutations: {
        [ TOGGLE_SIDEBAR ]: toggleSidebar,
        [ UPDATE_WINDOW_WIDTH ]: updateWindowWidth,
        [ UPDATE_DATA_CONTENT ]: updateDataContent,
        [ UPDATE_DATA_COUNT ]: updateDataCount,
        [ UPDATE_DATA_VIEW ]: updateDataView,
        [ UPDATE_DATA_VIEWS ]: updateDataViews,
        [ ADD_DATA_VIEW ]: addDataView,
        [ UPDATE_REMOVED_DATA_VIEW ]: updateRemovedDataView,
        [ UPDATE_DATA_FIELDS ]: updateDataFields,
        [ UPDATE_DATA_HYPERLINKS ]: updateDataHyperlinks,
        [ UPDATE_DATA_LABELS ]: updateDataLabels,
        [ UPDATE_ADDED_DATA_LABELS ]: updateAddedDataLabels,
        [ UPDATE_REMOVED_DATA_LABELS ]: updateRemovedDataLabels,
        [ UPDATE_DATA_BY_ID ]: updateDataByID,
        [ UPDATE_SAVED_DATA_NOTE ]: updateSavedDataNote,
        [ UPDATE_REMOVED_DATA_NOTE ]: updateRemovedDataNote,
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
        [ FETCH_DATA_HYPERLINKS ]: fetchDataHyperlinks,
        [ START_RESEARCH_PHASE ]: startResearch,
        [ FETCH_DATA_LABELS ]: fetchDataLabels,
        [ ADD_DATA_LABELS ]: addDataLabels,
        [ REMOVE_DATA_LABELS ]: removeDataLabels,
        [ DISABLE_DATA ]: disableData,
        [ DELETE_DATA ]: deleteData,
        [ LINK_DATA ]: linkData,
        [ UNLINK_DATA ]: unlinkData,
        [ FETCH_DATA_BY_ID ]: fetchDataByID,
        [ SAVE_DATA_NOTE ]: saveDataNote,
        [ REMOVE_DATA_NOTE ]: removeDataNote,
        [ RUN_ACTION ]: runAction,
        [ STOP_RESEARCH_PHASE ]: stopResearch,
		[ FETCH_SYSTEM_CONFIG ]: fetchSystemConfig,
        [ SAVE_CUSTOM_DATA ]: saveCustomData
    },
    modules: {
        /*
            System's controls resource, relevant for each component.
            Module stores controls and manages the way of obtaining it.
         */
        devices,
		users,
		explorer,
		adapters,
		alerts,
        notifications,
        auth,
        constants,
        dashboard,
		reports,
		settings,
		onboarding
    }

})