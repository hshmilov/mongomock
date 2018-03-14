import Vue from 'vue'
import Vuex from 'vuex'

import {
	REQUEST_API, requestApi,
	FETCH_DATA_CONTENT, fetchTableContent,
	FETCH_DATA_COUNT, fetchTableCount,
	FETCH_DATA_VIEWS, fetchTableViews,
	SAVE_DATA_VIEW, saveTableView,
	FETCH_DATA_FIELDS, fetchDataFields
} from './actions'
import {
	TOGGLE_SIDEBAR, toggleSidebar,
	UPDATE_DATA_CONTENT, updateTableContent,
	UPDATE_DATA_COUNT, updateTableCount,
	UPDATE_DATA_VIEW, updateTableView,
	UPDATE_DATA_VIEWS, updateTableViews,
	ADD_DATA_VIEW, addTableView,
	UPDATE_DATA_FIELDS, updateDataFields
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
        [ UPDATE_DATA_CONTENT ]: updateTableContent,
		[ UPDATE_DATA_COUNT ]: updateTableCount,
		[ UPDATE_DATA_VIEW ]: updateTableView,
		[ UPDATE_DATA_VIEWS ]: updateTableViews,
		[ ADD_DATA_VIEW ]: addTableView,
		[ UPDATE_DATA_FIELDS ]: updateDataFields
    },
    actions: {
        [ REQUEST_API ]: requestApi,
        [ FETCH_DATA_CONTENT ]: fetchTableContent,
		[ FETCH_DATA_COUNT ]: fetchTableCount,
		[ FETCH_DATA_VIEWS ]: fetchTableViews,
		[ SAVE_DATA_VIEW ]: saveTableView,
		[ FETCH_DATA_FIELDS ]: fetchDataFields
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