import Vue from 'vue'
import Vuex from 'vuex'

import { REQUEST_API, requestApi } from '../store/actions'
import { TOGGLE_SIDEBAR, toggleSidebar } from './mutations'
import { device } from '../store/modules/device'
import { query } from '../store/modules/query'

Vue.use(Vuex)
export default new Vuex.Store({
    state: {
        /*
            General data that the system uses throughout pages
         */
        user: {
            firstname: 'Avidor',
            lastname: 'Bartov',
            picname: '/src/assets/images/users/ofri.jpg'

        },
        configuration: {
            language: 'en'
        },
        interaction: {
            collapseSidebar: false
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
        query
    }
})