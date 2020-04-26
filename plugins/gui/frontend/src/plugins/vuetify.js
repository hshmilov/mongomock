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
import EntityAction from '../components/axons/icons/axoniusIcons/entityAction.vue';
import EntityColumn from '../components/axons/icons/axoniusIcons/entityColumn.vue';
import EntityExport from '../components/axons/icons/axoniusIcons/entityExport.vue';
import ResetPassword from '../components/axons/icons/axoniusIcons/resetPassword.vue';
import Toggle from '../components/axons/icons/axoniusIcons/toggle.vue';
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
  entityAction: {
    component: EntityAction,
  },
  entityColumn: {
    component: EntityColumn,
  },
  entityExport: {
    component: EntityExport,
  },
  legendOpen: {
    component: Toggle,
    props: {
      leftFill: '#DEDEDE',
      leftStroke: '#DEDEDE',
      rightFill: 'Transparent',
      rightStroke: '#DEDEDE',
    },
  },
  legendClosed: {
    component: Toggle,
    props: {
      leftFill: 'Transparent',
      leftStroke: '#DEDEDE',
      rightFill: '#DEDEDE',
      rightStroke: '#DEDEDE',
    },
  },
  legendOpenDarker: {
    component: Toggle,
    props: {
      leftFill: '#4A4A4A',
      leftStroke: '#4A4A4A',
      rightFill: 'Transparent',
      rightStroke: '#4A4A4A',
    },
  },
  legendClosedDarker: {
    component: Toggle,
    props: {
      leftFill: 'Transparent',
      leftStroke: '#4A4A4A',
      rightFill: '#4A4A4A',
      rightStroke: '#4A4A4A',
    },
  },
  resetPassword: {
    component: ResetPassword,
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
