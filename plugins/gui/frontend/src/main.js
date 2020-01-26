import Vue from 'vue'
import { createVuetifyConfigObject } from './plugins/vuetify'
import App from './components/App.vue'
import Vuelidate from 'vuelidate'
import VueAnalytics from 'vue-analytics'
import SafeguardPlugin from './plugins/safeguard-modal'
import router from './router/index'
import store from './store/index'
import {
	MdSwitch, MdDatepicker, MdField, MdIcon, MdButton, MdDialog, MdCard, MdList, MdChips, MdCheckbox, MdMenu, MdProgress, MdDivider, MdDrawer,
} from 'vue-material/dist/components'

import VueCookies from 'vue-cookies'
import 'vue-svgicon/dist/polyfill'
import * as svgicon from 'vue-svgicon'

Vue.use(Vuelidate)
Vue.use(MdSwitch)
Vue.use(MdDatepicker)
Vue.use(MdField)
Vue.use(MdIcon)
Vue.use(MdButton)
Vue.use(MdDialog)
Vue.use(MdCard)
Vue.use(MdList)
Vue.use(MdChips)
Vue.use(MdCheckbox)
Vue.use(MdMenu)
Vue.use(MdProgress)
Vue.use(MdDivider)
Vue.use(MdDrawer)

Vue.use(VueCookies)

Vue.use(SafeguardPlugin)


Vue.use(svgicon, {tagName: 'svg-icon'})

Vue.use(VueAnalytics, {
	id: 'UA-123123123-0', // set in backend
	router,
	customResourceURL: '/src/analytics.js'
})

import './mixpanel_init'

new Vue({
	el: '#app',
	vuetify: createVuetifyConfigObject(),
	components: {App},
	template: '<App />',
	router,
	store
})
