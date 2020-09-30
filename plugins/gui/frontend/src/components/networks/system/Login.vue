<template>
  <div
    class="x-login"
  >
    <div
      class="login-container"
    >
      <div class="header">
        <XIcon
          family="logo"
          type="logo"
        />
        <XIcon
          family="logo"
          type="axonius"
          class="logo-subtext"
        />
      </div>
      <div class="body">
        <VProgressCircular
          v-if="showProgressBar"
          indeterminate
          class="center-progress-bar"
          color="primary"
        />
        <div v-else-if="error">
          {{error}}
        </div>
        <XSignupForm
          v-else-if="showSignup"
          @done="signup"
        />
        <div v-else-if="showResetPassword">
          <XResetPasswordForm :token="resetPasswordToken" />
        </div>
        <div v-else>
          <XLoginForm
            v-if="loginSettings"
            :settings="loginSettings"
          />
          <XLoginOptions
            :settings="loginSettings"
          />
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import _get from 'lodash/get';
import XSignupForm from './SignupForm.vue';
import XLoginForm from './LoginForm.vue';
import XLoginOptions from './LoginOptions.vue';
import XResetPasswordForm from './ResetPasswordForm.vue';

import { GET_SIGNUP, GET_LOGIN_OPTIONS } from '../../../store/modules/auth';

export default {
  name: 'XLogin',
  components: {
    XLoginForm, XSignupForm, XLoginOptions, XResetPasswordForm,
  },
  data() {
    return {
      loginSettings: null,
    };
  },
  computed: {
    ...mapState({
      showSignup(state) {
        return !state.auth.signup.data;
      },
      fetchingSignup(state) {
        return state.auth.signup.fetching;
      },
      fetchingLoginSettings(state) {
        return state.auth.loginOptions.fetching;
      },
      error(state) {
        return state.auth.signup.error || state.auth.loginOptions.error;
      },
    }),
    showProgressBar() {
      return this.fetchingSignup || this.fetchingLoginSettings;
    },
    resetPasswordToken() {
      return _get(this.$route.query, 'token', false);
    },
    showResetPassword() {
      return !!this.resetPasswordToken;
    },
  },
  mounted() {
    this.signup();
  },
  methods: {
    ...mapActions({
      getSignup: GET_SIGNUP,
      getLoginSettings: GET_LOGIN_OPTIONS,
    }),
    async signup() {
      const { data: signupResData } = await this.getSignup();
      if (signupResData.signup) {
        // request login setting only when user is not in signup mode
        const { status, data } = await this.getLoginSettings();
        this.loginSettings = status === 200 ? data : null;
      }
    },
  },
};
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

        .x-icon {
          font-size: 36px;
          &.logo-subtext {
            font-size: 20px;
            svg {
              width: 7em;
            }
          }
        }
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

        .center-progress-bar {
          display: block;
          margin: 0 auto;
        }

        .x-form {
          height: calc(100% - 96px);

          .x-array-edit .list {
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
