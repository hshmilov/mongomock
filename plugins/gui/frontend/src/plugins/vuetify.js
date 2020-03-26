/* eslint-disable global-require */
/* eslint-disable import/no-dynamic-require */
import Vue from 'vue';
import Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';
import EnforcementsCustomIcon from '../components/axons/icons/axoniusIcons/enforcements.vue';
import DraggableCustomIcon from '../components/axons/icons/axoniusIcons/draggable.vue';
import VerticaldotsCustomIcon from '../components/axons/icons/axoniusIcons/verticaldots.vue';
import CardDraggable from '../components/axons/icons/axoniusIcons/cardDraggable.vue';
import CardSearch from '../components/axons/icons/axoniusIcons/cardSearch.vue';

import defaultTheme from '../assets/themes/default.json';

const axoniusIcons = {
  enforcements: {
    component: EnforcementsCustomIcon,
    props: {
      strokeWidth: '24px',
      strokeColor: '#fff',
      fillColor: '#fff',
    },
  },
  draggable: {
    component: DraggableCustomIcon,
  },
  verticaldots: {
    component: VerticaldotsCustomIcon,
  },
  cardDraggable: {
    component: CardDraggable,
  },
  cardSearch: {
    component: CardSearch,
  },
};

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
      values: axoniusIcons,
    },
  };
  return new Vuetify(vuetifyOptions);
};
