import Vue from 'vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import '@mdi/font/css/materialdesignicons.css'

import defaultTheme from '../assets/themes/default.json'

export const createVuetifyConfigObject = () => {
  Vue.use(Vuetify)

  let clientTheme = ENV.client? require(`../assets/themes/${ENV.client}.json`) : {}
  const vuetifyOptions = {
    theme: {
      themes: {
        light: {
          ...defaultTheme,
          ...clientTheme
        }
      },
      options: {
        customProperties: true
      }
    },
    icons: {
      iconfont: 'mdi'
    }
  }
  return new Vuetify(vuetifyOptions)
}
