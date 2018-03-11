import Vue from 'vue'
import Vuex from 'vuex'

import {
	REQUEST_API, requestApi,
	FETCH_TABLE_CONTENT, fetchTableContent,
	FETCH_TABLE_COUNT, fetchTableCount,
	FETCH_TABLE_VIEWS, fetchTableViews,
	SAVE_TABLE_VIEW, saveTableView
} from './actions'
import {
	TOGGLE_SIDEBAR, toggleSidebar,
	UPDATE_TABLE_CONTENT, updateTableContent,
	UPDATE_TABLE_COUNT, updateTableCount,
	UPDATE_TABLE_VIEW, updateTableView,
	UPDATE_TABLE_VIEWS, updateTableViews,
	ADD_TABLE_VIEW, addTableView
} from './mutations'
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
        [ UPDATE_TABLE_CONTENT ]: updateTableContent,
		[ UPDATE_TABLE_COUNT ]: updateTableCount,
		[ UPDATE_TABLE_VIEW ]: updateTableView,
		[ UPDATE_TABLE_VIEWS ]: updateTableViews,
		[ ADD_TABLE_VIEW ]: addTableView
    },
    actions: {
        [ REQUEST_API ]: requestApi,
        [ FETCH_TABLE_CONTENT ]: fetchTableContent,
		[ FETCH_TABLE_COUNT ]: fetchTableCount,
		[ FETCH_TABLE_VIEWS ]: fetchTableViews,
		[ SAVE_TABLE_VIEW ]: saveTableView
    },
    modules: {
        /*
            System's controls resource, relevant for each component.
            Module stores controls and manages the way of obtaining it.
         */
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