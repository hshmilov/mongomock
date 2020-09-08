/* eslint-disable global-require */
/* eslint-disable import/no-dynamic-require */
import Vue from 'vue';
import Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';

import EnforcementsCustomIcon from '@axons/icons/axoniusIcons/enforcements.vue';
import EnforcementsLock from '@axons/icons/axoniusIcons/enforcementsLock.vue';
import DraggableCustomIcon from '@axons/icons/axoniusIcons/draggable.vue';
import VerticaldotsCustomIcon from '@axons/icons/axoniusIcons/verticaldots.vue';
import CardDraggable from '@axons/icons/axoniusIcons/cardDraggable.vue';
import CardSearch from '@axons/icons/axoniusIcons/cardSearch.vue';
import EntityAction from '@axons/icons/axoniusIcons/entityAction.vue';
import EntityColumn from '@axons/icons/axoniusIcons/entityColumn.vue';
import EntityExport from '@axons/icons/axoniusIcons/entityExport.vue';
import ResetPassword from '@axons/icons/axoniusIcons/resetPassword.vue';
import Filterable from '@axons/icons/axoniusIcons/filterable.vue';
import Funnel from '@axons/icons/axoniusIcons/funnel.vue';
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
  enforcementsDark: {
    component: EnforcementsCustomIcon,
    props: {
      strokeWidth: '24px',
      strokeColor: '#000',
      fillColor: '#000',
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
  resetPassword: {
    component: ResetPassword,
  },
  filterable: {
    component: Filterable,
  },
  funnel: {
    component: Funnel,
  },
  enforcementsLock: {
    component: EnforcementsLock,
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
