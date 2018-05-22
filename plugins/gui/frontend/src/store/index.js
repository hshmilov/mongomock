import Vue from 'vue'
import Vuex from 'vuex'

import {
	REQUEST_API, requestApi,
	FETCH_DATA_CONTENT, fetchDataContent,
	FETCH_DATA_CONTENT_CSV, fetchDataContentCSV,
	FETCH_DATA_COUNT, fetchDataCount,
	FETCH_DATA_VIEWS, fetchDataViews,
	SAVE_DATA_VIEW, saveDataView,
	FETCH_DATA_FIELDS, fetchDataFields,
	FETCH_DATA_QUERIES, fetchDataQueries,
	SAVE_DATA_QUERY, saveDataQuery,
    START_RESEARCH_PHASE, startResearch,
	FETCH_DATA_LABELS, fetchDataLabels,
	ADD_DATA_LABELS, addDataLabels,
	REMOVE_DATA_LABELS, removeDataLabels,
	DISABLE_DATA, disableData,
	FETCH_DATA_BY_ID, fetchDataByID,
	REMOVE_DATA_QUERY, removeDataQuery,
	RUN_ACTION, runAction,
    STOP_RESEARCH_PHASE, stopResearch
} from './actions'
import {
	TOGGLE_SIDEBAR, toggleSidebar,
	UPDATE_EMPTY_STATE, updateEmptyState,
	UPDATE_DATA_CONTENT, updateDataContent,
	UPDATE_DATA_COUNT, updateDataCount,
	UPDATE_DATA_VIEW, updateDataView,
	UPDATE_DATA_VIEWS, updateDataViews,
	ADD_DATA_VIEW, addDataView,
	UPDATE_DATA_FIELDS, updateDataFields,
	UPDATE_DATA_QUERIES, updateDataQueries,
	ADD_DATA_QUERY, addDataQuery,
	UPDATE_DATA_LABELS, updateDataLabels,
	UPDATE_ADDED_DATA_LABELS, updateAddedDataLabels,
	UPDATE_REMOVED_DATA_LABELS, updateRemovedDataLabels,
	UPDATE_DATA_BY_ID, updateDataByID,
	UPDATE_REMOVED_DATA_QUERY, updateRemovedDataQuery
} from './mutations'
import {
	GET_DATA_FIELD_LIST_TYPED, getDataFieldsListTyped,
	GET_DATA_FIELD_LIST_SPREAD, getDataFieldListSpread,
	GET_DATA_BY_ID, getDataByID
} from './getters'
import { devices } from './modules/devices'
import { users } from './modules/users'
import { adapter } from '../store/modules/adapter'
import { alert } from '../store/modules/alert'
import { notifications } from '../store/modules/notifications'
import { auth } from './modules/auth'
import { dashboard } from '../store/modules/dashboard'
import { report } from '../store/modules/report'
import { configurable } from '../store/modules/configurable'

Vue.use(Vuex)
export default new Vuex.Store({
    state: {
        /*
            General controls that the system uses throughout pages
         */
        interaction: {
            collapseSidebar: true,
			onboarding: {
				emptyStates: {
					emptyMailSettings: false,
					emptySyslogSettings: false
				}
			}
        }
    },
	getters: {
		[ GET_DATA_FIELD_LIST_TYPED ]: getDataFieldsListTyped,
		[ GET_DATA_FIELD_LIST_SPREAD ]: getDataFieldListSpread,
		[ GET_DATA_BY_ID ]: getDataByID
	},
    mutations: {
        [ TOGGLE_SIDEBAR ]: toggleSidebar,
		[ UPDATE_EMPTY_STATE ]: updateEmptyState,
        [ UPDATE_DATA_CONTENT ]: updateDataContent,
		[ UPDATE_DATA_COUNT ]: updateDataCount,
		[ UPDATE_DATA_VIEW ]: updateDataView,
		[ UPDATE_DATA_VIEWS ]: updateDataViews,
		[ ADD_DATA_VIEW ]: addDataView,
		[ UPDATE_DATA_FIELDS ]: updateDataFields,
		[ UPDATE_DATA_QUERIES ]: updateDataQueries,
		[ ADD_DATA_QUERY ]: addDataQuery,
		[ UPDATE_DATA_LABELS ]: updateDataLabels,
		[ UPDATE_ADDED_DATA_LABELS ]: updateAddedDataLabels,
		[ UPDATE_REMOVED_DATA_LABELS ]: updateRemovedDataLabels,
		[ UPDATE_DATA_BY_ID ]: updateDataByID,
		[ UPDATE_REMOVED_DATA_QUERY ]: updateRemovedDataQuery
    },
    actions: {
        [ REQUEST_API ]: requestApi,
        [ FETCH_DATA_CONTENT ]: fetchDataContent,
		[ FETCH_DATA_CONTENT_CSV ]: fetchDataContentCSV,
		[ FETCH_DATA_COUNT ]: fetchDataCount,
		[ FETCH_DATA_VIEWS ]: fetchDataViews,
		[ SAVE_DATA_VIEW ]: saveDataView,
		[ FETCH_DATA_FIELDS ]: fetchDataFields,
		[ FETCH_DATA_QUERIES ]: fetchDataQueries,
		[ SAVE_DATA_QUERY ]: saveDataQuery,
		[ START_RESEARCH_PHASE ]: startResearch,
		[ FETCH_DATA_LABELS ]: fetchDataLabels,
		[ ADD_DATA_LABELS ]: addDataLabels,
		[ REMOVE_DATA_LABELS ]: removeDataLabels,
		[ DISABLE_DATA ]: disableData,
		[ FETCH_DATA_BY_ID ]: fetchDataByID,
		[ REMOVE_DATA_QUERY ]: removeDataQuery,
		[ RUN_ACTION ]: runAction,
        [ STOP_RESEARCH_PHASE ]: stopResearch
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
        dashboard,
		report,
		configurable
    }

})