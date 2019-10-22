<template>
  <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
  -->
  <div id="app" v-if="fetchedLoginStatus">
    <!--Link for downloading files-->
    <a id="file-auto-download-link"></a>
    <!-- Nested navigation linking to routes defined in router/index.js -->
    <template v-if="userName">
      <x-side-bar class="print-exclude" @access-violation="notifyAccess" />
      <x-fab-transition>
        <div
          title="Getting Started"
          id="getting-started-fab"
          v-if="isUserAdmin && gettingStartedEnabled && !open"
          @click="changeChecklistOpenState"
        >
          <md-icon>list</md-icon>
        </div>
      </x-fab-transition>
      <router-view />
      <x-top-bar class="print-exclude" @access-violation="notifyAccess" />
      <x-toast v-if="toastMessage" :timeout="toastData.toastTimeout" v-model="toastMessage" />
      <x-access-modal v-model="blockedComponent" />
      <x-getting-started v-if="isUserAdmin" v-model="open" />
    </template>
    <template v-else>
      <x-login />
    </template>
  </div>
</template>

<script>
import Vue from 'vue'
import xTopBar from './networks/navigation/TopBar.vue'
import xSideBar from './networks/navigation/SideBar.vue'
import xLogin from './networks/system/Login.vue'
import xAccessModal from './neurons/popover/AccessModal.vue'
import xToast from './axons/popover/Toast.vue'
import { GET_USER } from '../store/modules/auth'
import { IS_EXPIRED } from '../store/getters'
import {
  FETCH_DATA_FIELDS,
  FETCH_SYSTEM_CONFIG,
  FETCH_SYSTEM_EXPIRED
} from '../store/actions'
import {
  FETCH_CONSTANTS,
  FETCH_FIRST_HISTORICAL_DATE,
  FETCH_ALLOWED_DATES
} from '../store/modules/constants'
import { UPDATE_WINDOW_WIDTH, SHOW_TOASTER_MESSAGE } from '../store/mutations'
import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
import { GET_GETTING_STARTED_DATA } from '../store/modules/onboarding'
import { IS_USER_ADMIN } from "../store/modules/auth"
import { entities } from '../constants/entities'

import _get from 'lodash/get'
import XGettingStarted from '../components/networks/getting-started/GettingStarted.vue'

import './axons/icons'

export const GettingStartedPubSub = new Vue()

// I put this locally because it has specific implementation for this use-case. I can move this though to a more generic directory if needed
const XFabTransition = {
  functional: true,
  render: function(createElement, context) {
    const data = {
      props: {
        name: 'x-fab-transition'
      },
      on: {
        enter: function(el, done) {
          setTimeout(() => {
            el.style.opacity = 1
            done()
          }, 500)
        },
        leave: function(el, done) {
          el.style.opacity = 0
          done()
        }
      }
    };
    return createElement('transition', data, context.children)
  }
};

export default {
  name: 'app',
  components: {
    xLogin,
    xTopBar,
    xSideBar,
    xAccessModal,
    xToast,
    XGettingStarted,
    XFabTransition
  },
  data() {
    return {
      blockedComponent: '',
      open: this.gettingStartedAutoOpen,
      firstLoad: true
    }
  },
  computed: {
    ...mapState({
      gettingStartedAutoOpen: state => {
        return _get(
          state,
          'onboarding.gettingStarted.data.settings.autoOpen',
          false
        )
      },
      fetchedLoginStatus(state) {
        return (
          Object.keys(state.auth.currentUser.data).length > 0 ||
          state.auth.currentUser.error
        )
      },
      userName(state) {
        return state.auth.currentUser.data.user_name
      },
      userPermissions(state) {
        return state.auth.currentUser.data.permissions
      },
      toastData(state) {
        return state.toast
      },
      gettingStartedEnabled: state =>
        _get(state, 'configuration.data.global.gettingStartedEnabled', false)
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
      isUserAdmin: IS_USER_ADMIN
    }),
    toastMessage: {
      get() {
        return this.toastData.message
      },
      set(value) {
        this.showToasterMessage(value)
      }
    }
  },
  watch: {
    $route(to, from) {
      if (!this.firstLoad) {
        this.changeChecklistOpenState(null, true)
      } else {
        this.firstLoad = false
      }
    },
    userName(newUserName) {
      if (newUserName) {
        this.fetchGlobalData()
      } else {
        this.handleExpiration()
      }
    },
  },
  methods: {
    ...mapMutations({
      updateWindowWidth: UPDATE_WINDOW_WIDTH,
      showToasterMessage: SHOW_TOASTER_MESSAGE
    }),
    ...mapActions({
      fetchGettingStartedData: GET_GETTING_STARTED_DATA,
      getUser: GET_USER,
      fetchConfig: FETCH_SYSTEM_CONFIG,
      fetchExpired: FETCH_SYSTEM_EXPIRED,
      fetchConstants: FETCH_CONSTANTS,
      fetchFirstHistoricalDate: FETCH_FIRST_HISTORICAL_DATE,
      fetchAllowedDates: FETCH_ALLOWED_DATES,
      fetchDataFields: FETCH_DATA_FIELDS
    }),
    changeChecklistOpenState(e, forceClose) {
      if (forceClose) {
        this.open = false
      } else {
        this.open = !this.open
      }
    },
    fetchGlobalData() {
      this.fetchConstants()
      if (!this.isExpired) {
        entities.forEach(entity => {
          if (this.entityRestricted(entity.title)) return
          this.fetchDataFields({ module: entity.name })
        });
        this.fetchConfig()
        this.fetchFirstHistoricalDate()
        this.fetchAllowedDates()
        if (this.isUserAdmin) {
        this.fetchGettingStartedData().then(res => {
          this.open = this.gettingStartedAutoOpen
        });
      }
      }
    },
    notifyAccess(name) {
      this.blockedComponent = name
    },
    entityRestricted(entity) {
      return this.userPermissions[entity] === 'Restricted'
    },
    async handleExpiration() {
      const res = await this.fetchExpired()
      if (res.data) {
        this.$router.push("/")
      }
    }
  },
  async mounted() {
    GettingStartedPubSub.$on(
      'getting-started-open-state',
      this.changeChecklistOpenState
    )
    this.handleExpiration()
    this.getUser()

    this.$nextTick(function() {
      window.addEventListener('resize', this.updateWindowWidth)
      //Init
      this.updateWindowWidth()
    });
  }
};
</script>

<style lang="scss">
@import "../assets/scss/styles";
@import "../assets/scss/custom_styles";

#app {
  height: 100vh;
  width: 100vw;
  position: fixed;

  #getting-started-fab {
    opacity: 0;
    position: absolute;
    right: 20px;
    top: 85px;
    color: #fff;
    z-index: 9999;
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
    }
  }
  .md-drawer.md-temporary.md-active {
    z-index: 102;
    background-color: #fafafa;
  }
  .md-overlay {
    z-index: 101;
    opacity: 1;
  }
}
</style>
