import Vue from 'vue'
import Vuex from 'vuex'

import {
	REQUEST_API, requestApi, FETCH_TABLE_CONTENT, fetchTableContent, FETCH_TABLE_COUNT,
	fetchTableCount
} from './actions'
import {
	TOGGLE_SIDEBAR, toggleSidebar,
	UPDATE_TABLE_CONTENT, updateTableContent,
	UPDATE_TABLE_COUNT, updateTableCount,
	UPDATE_TABLE_VIEW, updateTableView
} from './mutations'
import { device } from '../store/modules/device'
import { query } from '../store/modules/query'
import { plugin } from '../store/modules/plugin'
import { adapter } from '../store/modules/adapter'
import { alert } from '../store/modules/alert'
import { notification } from '../store/modules/notifications'
import { user } from '../store/modules/user'
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
		[ UPDATE_TABLE_VIEW ]: updateTableView
    },
    actions: {
        [ REQUEST_API ]: requestApi,
        [ FETCH_TABLE_CONTENT ]: fetchTableContent,
		[ FETCH_TABLE_COUNT ]: fetchTableCount
    },
    modules: {
        /*
            System's controls resource, relevant for each component.
            Module stores controls and manages the way of obtaining it.
         */
        device,
        query,
		plugin,
		adapter,
		alert,
        notification,
        user,
        dashboard
    }

})