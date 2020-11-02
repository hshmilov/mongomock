/* eslint-disable global-require */
/* eslint-disable import/no-dynamic-require */
import Vue from 'vue';
import Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';

import defaultTheme from '../assets/themes/default.json';

// eslint-disable-next-line import/prefer-default-export
export const createVuetifyConfigObject = () => {
  Vue.use(Vuetify);


  // eslint-disable-next-line no-undef
  const clientTheme = ENV.client ? require(`../assets/themes/${ENV.client}.json`) : {};
  const vuetifyOptions = {
    theme: {
      themes: {
        light: {
          ...defaultTheme,
          ...clientTheme,
        },
      },
      options: {
        customProperties: true,
      },
    },
    icons: {
      iconfont: 'mdiSvg',
    },
  };
  return new Vuetify(vuetifyOptions);
};
