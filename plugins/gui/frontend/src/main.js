/* eslint-disable no-undef */
import Vue from 'vue'

import { MdSwitch, MdDatepicker, MdField, MdIcon, MdButton, MdDialog, MdCard } from 'vue-material/dist/components'
Vue.use(MdSwitch)
Vue.use(MdDatepicker)
Vue.use(MdField)
Vue.use(MdIcon)
Vue.use(MdButton)
Vue.use(MdDialog)
Vue.use(MdCard)

import router from './router/index'
import store from './store/index'
import App from './components/App.vue'

import 'vue-svgicon/dist/polyfill'
import * as svgicon from 'vue-svgicon'
Vue.use(svgicon, {tagName: 'svg-icon'})

import TreeView from 'vue-json-tree-view'
Vue.use(TreeView)

import VmSelect from 'vue-multiple-select'
Vue.use(VmSelect)


new Vue({
	el: '#app',
	template: '<App />',
	components: {App},
	router,
	store
})
