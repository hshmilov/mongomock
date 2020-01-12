import Vue from 'vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import EnfrocementsCustomIcon from '../components/axons/icons/axoniusIcons/enforcements.vue'

import defaultTheme from '../assets/themes/default.json'

const axoniusIcons = {
  enforcements: {
      component: EnfrocementsCustomIcon,
      props: {
          strokeWidth: '24px',
          strokeColor: '#fff',
          fillColor: '#fff',
      }
  }
}

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
      iconfont: 'mdiSvg',
      values: axoniusIcons
  },
  }
  return new Vuetify(vuetifyOptions)
}
