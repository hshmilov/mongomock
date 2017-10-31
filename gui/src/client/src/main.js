/* eslint-disable no-undef */
import Vue from 'vue'

import router from './router/index'
import store from './store/index'
import App from './containers/App.vue'

import 'vue-svgicon/dist/polyfill'
import * as svgicon from 'vue-svgicon'
Vue.use(svgicon, {tagName: 'svg-icon'})

import {MediaQueries} from 'vue-media-queries';
const mediaQueries = new MediaQueries();
Vue.use(mediaQueries);

new Vue({
    el: '#app',
    template: '<App />',
    components: {App},
    mediaQueries: mediaQueries,
    router,
    store
})
