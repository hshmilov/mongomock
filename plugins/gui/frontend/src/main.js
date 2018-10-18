/* eslint-disable no-undef */
import Vue from 'vue'

import { MdSwitch } from 'vue-material/dist/components'
Vue.use(MdSwitch)

import router from './router/index'
import store from './store/index'
import App from './containers/App.vue'

import 'vue-svgicon/dist/polyfill'
import * as svgicon from 'vue-svgicon'
Vue.use(svgicon, {tagName: 'svg-icon'})

import { MediaQueries } from 'vue-media-queries'

const mediaQueries = new MediaQueries()
Vue.use(mediaQueries)

import TreeView from 'vue-json-tree-view'
Vue.use(TreeView)

import VmSelect from 'vue-multiple-select'
Vue.use(VmSelect)


new Vue({
	el: '#app',
	template: '<App />',
	components: {App},
	mediaQueries: mediaQueries,
	router,
	store
})
