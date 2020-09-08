<template>
  <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
  -->
  <VApp
    v-if="fetchedLoginStatus"
    id="app"
  >
    <XSafeguard />
    <XMessageModal />
    <XTunnelConnectionModal />
    <!--Link for downloading files-->
    <a id="file-auto-download-link"></a>
    <!-- Nested navigation linking to routes defined in router/index.js -->
    <template v-if="userName && isSessionCookieValid()">
      <XSideBar
        class="print-exclude"
      />
      <XFabTransition>
        <div
          v-if="$isAdmin() && gettingStartedEnabled && !open"
          id="getting-started-fab"
          title="Getting Started"
          @click="changeChecklistOpenState"
        >
          <XIcon type="unordered-list" />
        </div>
      </XFabTransition>
      <RouterView />
      <XTopBar
        class="print-exclude"
        @access-violation="notifyAccess"
      />
      <XAccessModal v-model="blockedComponent" />
      <XGettingStarted
        v-if="$isAdmin() && gettingStartedEnabled"
        v-model="open"
      />
    </template>
    <template v-else>
      <XLogin />
    </template>
    <XBottomBar />
    <XToast
      v-if="toastMessage"
      v-model="toastMessage"
      :timeout="toastData.toastTimeout"
    />
  </VApp>
</template>

<script>
import Vue from 'vue';
import {
  mapState, mapGetters, mapMutations, mapActions,
} from 'vuex';
import _get from 'lodash/get';
import { FETCH_FETURE_FLAGS } from '@store/modules/settings';
import { SHOW_TOASTER_MESSAGE } from '../store/mutations';
import XTopBar from './networks/navigation/TopBar.vue';
import XBottomBar from './networks/navigation/BottomBar.vue';
import XSideBar from './networks/navigation/SideBar.vue';
import XLogin from './networks/system/Login.vue';
import XAccessModal from './neurons/popover/AccessModal.vue';
import XTunnelConnectionModal from './neurons/popover/TunnelConnectionModal.vue';
import XToast from './axons/popover/Toast.vue';
import Icon from './axons/icons/Icon';
import sessionTimeoutMixin from '../mixins/session_timeout';

import { GET_USER } from '../store/modules/auth';
import { IS_EXPIRED } from '../store/getters';

import {
  FETCH_SYSTEM_CONFIG,
  FETCH_SYSTEM_EXPIRED,
} from '../store/actions';
import {
  FETCH_CONSTANTS,
  FETCH_FIRST_HISTORICAL_DATE,
  FETCH_ALLOWED_DATES,
} from '../store/modules/constants';
import { GET_GETTING_STARTED_DATA } from '../store/modules/onboarding';

import XGettingStarted from './networks/getting-started/GettingStarted.vue';

export const GettingStartedPubSub = new Vue();

// This is local because of specific implementation for this use-case
const XFabTransition = {
  functional: true,
  render(createElement, context) {
    const data = {
      props: {
        name: 'x-fab-transition',
      },
      on: {
        enter(el, done) {
          setTimeout(() => {
            // eslint-disable-next-line no-param-reassign
            el.style.opacity = 1;
            done();
          }, 500);
        },
        leave(el, done) {
          // eslint-disable-next-line no-param-reassign
          el.style.opacity = 0;
          done();
        },
      },
    };
    return createElement('transition', data, context.children);
  },
};

export default {
  name: 'App',
  components: {
    XLogin,
    XTopBar,
    XBottomBar,
    XSideBar,
    XAccessModal,
    XToast,
    XGettingStarted,
    XFabTransition,
    XIcon: Icon,
    XTunnelConnectionModal,
  },
  mixins: [sessionTimeoutMixin],
  data() {
    return {
      blockedComponent: '',
      open: false,
      justLoggedIn: false,
    };
  },
  computed: {
    ...mapState({
      gettingStartedAutoOpen: (state) => _get(
        state,
        'onboarding.gettingStarted.data.settings.autoOpen',
        false,
      ),
      fetchedLoginStatus(state) {
        return state.auth.currentUser.data || state.auth.currentUser.error;
      },
      userName(state) {
        return _get(state, 'auth.currentUser.data.user_name', '');
      },
      toastData(state) {
        return state.toast;
      },
      gettingStartedEnabled: (state) => _get(state, 'configuration.data.global.gettingStartedEnabled', false),
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
    }),
    toastMessage: {
      get() {
        return this.toastData.message;
      },
      set(value) {
        this.showToasterMessage(value);
      },
    },
  },
  watch: {
    userName(newUserName) {
      if (newUserName) {
        this.fetchGlobalData();
      } else {
        this.handleExpiration();
      }
    },
  },
  async mounted() {
    GettingStartedPubSub.$on(
      'getting-started-open-state',
      this.changeChecklistOpenState,
    );

    GettingStartedPubSub.$on(
      'getting-started-login',
      () => {
        this.justLoggedIn = true;
      },
    );
    this.handleExpiration();
    this.getUser();
  },
  methods: {
    ...mapMutations({
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    ...mapActions({
      fetchGettingStartedData: GET_GETTING_STARTED_DATA,
      getUser: GET_USER,
      fetchConfig: FETCH_SYSTEM_CONFIG,
      fetchExpired: FETCH_SYSTEM_EXPIRED,
      fetchConstants: FETCH_CONSTANTS,
      fetchFirstHistoricalDate: FETCH_FIRST_HISTORICAL_DATE,
      fetchAllowedDates: FETCH_ALLOWED_DATES,
      featchFeatureFlags: FETCH_FETURE_FLAGS,
    }),
    changeChecklistOpenState() {
      this.open = !this.open;
    },
    fetchGlobalData() {
      this.featchFeatureFlags();
      this.fetchConstants();
      this.fetchConfig();
      if (!this.isExpired) {
        this.fetchFirstHistoricalDate();
        this.fetchAllowedDates();
        if (this.$isAdmin()) {
          this.fetchGettingStartedData().then(() => {
            if (this.justLoggedIn) {
              this.open = this.gettingStartedAutoOpen && this.gettingStartedEnabled;
            }
          });
        }
      }
    },
    notifyAccess(name) {
      this.blockedComponent = name;
    },
    async handleExpiration() {
      const res = await this.fetchExpired();
      // until https://axonius.atlassian.net/browse/AX-6369
      // we check here if the requested page in the administration
      // and prevent the expired redirection from this page
      if (res.data && window.location.pathname !== '/administration') {
        this.$router.push('/');
      }
    },
  },
};
</script>

<style lang="scss">
@import "../assets/scss/styles";

#app {
  height: 100vh;
  width: 100vw;
  position: relative;

  #getting-started-fab {
    opacity: 0;
    position: absolute;
    right: 20px;
    top: 85px;
    color: #fff;
    z-index: 999;
    background-color: black;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    cursor: pointer;
    display: flex;
    justify-content: center;
    align-items: center;
    &:hover {
      background-color: $theme-orange;
    }

    i {
      width: 20px;
      height: 20px;
      font-size: 16px;
      display: flex;
      justify-content: center;
      align-items: center;
    }
  }
  .md-drawer.md-temporary.md-active {
    z-index: 1001;
    background-color: #fafafa;
  }
  .md-overlay {
    z-index: 1000;
    opacity: 1;
  }
}
</style>
