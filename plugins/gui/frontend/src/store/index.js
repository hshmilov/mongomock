import Vue from 'vue'
import Vuex from 'vuex'

import {
	REQUEST_API, requestApi,
	FETCH_DATA_CONTENT, fetchDataContent,
	FETCH_DATA_COUNT, fetchDataCount,
	FETCH_DATA_VIEWS, fetchDataViews,
	SAVE_DATA_VIEW, saveDataView,
	FETCH_DATA_FIELDS, fetchDataFields,
	FETCH_DATA_QUERIES, fetchDataQueries,
	SAVE_DATA_QUERY, saveDataQuery
} from './actions'
import {
	TOGGLE_SIDEBAR, toggleSidebar,
	UPDATE_DATA_CONTENT, updateDataContent,
	UPDATE_DATA_COUNT, updateDataCount,
	UPDATE_DATA_VIEW, updateDataView,
	UPDATE_DATA_VIEWS, updateDataViews,
	ADD_DATA_VIEW, addDataView,
	UPDATE_DATA_FIELDS, updateDataFields,
	UPDATE_DATA_QUERIES, updateDataQueries,
	ADD_DATA_QUERY, addDataQuery
} from './mutations'
import { settings } from '../store/modules/settings'
import { device } from '../store/modules/device'
import { user } from '../store/modules/user'
import { query } from '../store/modules/query'
import { plugin } from '../store/modules/plugin'
import { adapter } from '../store/modules/adapter'
import { alert } from '../store/modules/alert'
import { notification } from '../store/modules/notifications'
import { auth } from './modules/auth'
import { dashboard } from '../store/modules/dashboard'

Vue.use(Vuex)
export default new Vuex.Store({
    state: {
        /*
            General controls that the system uses throughout pages
         */
        configuration: {
            language: 'en'
        },
        interaction: {
            collapseSidebar: true
        }
    },
    mutations: {
        [ TOGGLE_SIDEBAR ]: toggleSidebar,
        [ UPDATE_DATA_CONTENT ]: updateDataContent,
		[ UPDATE_DATA_COUNT ]: updateDataCount,
		[ UPDATE_DATA_VIEW ]: updateDataView,
		[ UPDATE_DATA_VIEWS ]: updateDataViews,
		[ ADD_DATA_VIEW ]: addDataView,
		[ UPDATE_DATA_FIELDS ]: updateDataFields,
		[ UPDATE_DATA_QUERIES ]: updateDataQueries,
		[ ADD_DATA_QUERY ]: addDataQuery
    },
    actions: {
        [ REQUEST_API ]: requestApi,
        [ FETCH_DATA_CONTENT ]: fetchDataContent,
		[ FETCH_DATA_COUNT ]: fetchDataCount,
		[ FETCH_DATA_VIEWS ]: fetchDataViews,
		[ SAVE_DATA_VIEW ]: saveDataView,
		[ FETCH_DATA_FIELDS ]: fetchDataFields,
		[ FETCH_DATA_QUERIES ]: fetchDataQueries,
		[ SAVE_DATA_QUERY ]: saveDataQuery
    },
    modules: {
        /*
            System's controls resource, relevant for each component.
            Module stores controls and manages the way of obtaining it.
         */
        settings,
        device,
		user,
        query,
		plugin,
		adapter,
		alert,
        notification,
        auth,
        dashboard
    }

})