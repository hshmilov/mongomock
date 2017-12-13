import Vue from 'vue'
import Vuex from 'vuex'

import { REQUEST_API, requestApi } from '../store/actions'
import { TOGGLE_SIDEBAR, toggleSidebar } from './mutations'
import { device } from '../store/modules/device'
import { query } from '../store/modules/query'
import { plugin } from '../store/modules/plugin'
import { adapter } from '../store/modules/adapter'
import { alert } from '../store/modules/alert'
import { notification } from '../store/modules/notifications'

Vue.use(Vuex)
export default new Vuex.Store({
    state: {
        /*
            General data that the system uses throughout pages
         */
        user: {
            firstname: 'Administrator',
            lastname: '',
            picname: '/src/assets/images/users/avatar.png'

        },
        configuration: {
            language: 'en'
        },
        interaction: {
            collapseSidebar: true
        }
    },
    mutations: {
        [TOGGLE_SIDEBAR]: toggleSidebar
    },
    actions: { [REQUEST_API]: requestApi },
    modules: {
        /*
            System's data resource, relevant for each component.
            Module stores data and manages the way of obtaining it.
         */
        device,
        query,
		plugin,
		adapter,
		alert,
        notification
    }

})