<template>
  <div
    v-if="!isConnected"
    class="x-login"
  >
    <div
      class="login-container"
      v-if="!fetchingSignup"
    >
      <div class="header">
        <svg-icon
          name="logo/logo"
          height="36"
          :original="true"
        />
        <svg-icon
          name="logo/axonius"
          height="20"
          :original="true"
          class="logo-subtext"
        />
      </div>
      <div class="body">
        <x-signup-form
          v-if="showSignup"
          @done="getSignup"
        />
        <x-login-form v-else-if="showLoginPage" />
        <x-login-options :login-okta="!showLoginPage"/>
      </div>
    </div>

  </div>
</template>

<script>
  import xSignupForm from './SignupForm.vue'
  import xLoginForm from './LoginForm.vue'
  import xLoginOptions from './LoginOptions.vue'

  import { mapState, mapActions } from 'vuex'
  import { GET_SIGNUP } from '../../../store/modules/auth'

  export default {
    name: 'XLogin',
    components: {
      xLoginForm, xSignupForm, xLoginOptions
    },
    computed: mapState({
        isConnected (state) {
          return state.auth && state.auth.currentUser && state.auth.currentUser.data &&
            state.auth.currentUser.data.user_name && !state.auth.currentUser.fetching
        },
        showLoginPage (state) {
          return !state.staticConfiguration.medicalConfig || this.$route.hash === '#maintenance' || this.showSignup
        },
        showSignup (state) {
          return !state.auth.signup.data
        },
        fetchingSignup(state) {
          return state.auth.signup.data === null || state.auth.signup.fetching
        }
    }),
    mounted() {
      this.getSignup()
    },
    methods: {
      ...mapActions({
        getSignup: GET_SIGNUP
      }),
    }
  }
</script>

<style lang="scss">
  .x-login {
    background: url('/src/assets/images/general/login_bg.png') center bottom;
    background-size: cover;
    height: 100vh;
    display: flex;
    overflow: auto;

    .login-container {
      width: 400px;
      margin: auto;
      border-radius: 4px;
      background-color: $grey-1;
      display: flex;
      flex-flow: column;
      justify-content: center;

      .header {
        height: 128px;
        display: flex;
        flex-flow: column;
        justify-content: center;
      }

      > .body {
        background-color: white;
        flex: 1 0 auto;
        padding: 48px;
        border-radius: 4px;
        max-height: calc(100% - 128px);

        .login-title, .signup-title {
          margin-top: 0;
        }

        .x-form {
          height: calc(100% - 96px);

          .x-array-edit {
            display: block;

            .object {
              width: 100%;
            }

            .item {
              width: 100%;
              margin-bottom: 12px;
            }
          }
        }

      }

    }
  }
</style>
