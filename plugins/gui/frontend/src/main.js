import Vue from 'vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import VueAnalytics from 'vue-analytics'
import router from './router/index'
import store from './store/index'
import App from './components/App.vue'
import {
	MdSwitch, MdDatepicker, MdField, MdIcon, MdButton, MdDialog, MdCard, MdList, MdChips, MdCheckbox, MdMenu, MdProgress, MdDivider, MdDrawer,
} from 'vue-material/dist/components'
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

Vue.use(Vuetify)

import 'vue-svgicon/dist/polyfill'
import * as svgicon from 'vue-svgicon'
Vue.use(svgicon, {tagName: 'svg-icon'})

import VmSelect from 'vue-multiple-select'
Vue.use(VmSelect)

Vue.use(VueAnalytics, {
	id: 'UA-123123123-0', // set in backend
	router,
	customResourceURL: '/src/analytics.js'
})

const vuetifyOptions = {
	theme: {
		themes: {
			light: {
				primary: '#FF7D46',
				anchor: '-webkit-link'
			}
		}
	}
}
new Vue({
	el: '#app',
	vuetify: new Vuetify(vuetifyOptions),
	components: {App},
	template: '<App />',
	router,
	store
})
