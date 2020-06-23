<template>
  <div class="x-reset-password-form">
    <VProgressCircular
      v-if="tokenStatus.valid === undefined"
      indeterminate
      class="center-progress-bar"
      color="primary"
    />
    <div v-else-if="tokenStatus.valid">
      <h3 class="login-title">
        Reset Password
      </h3>
      <XForm
        v-model="credentials"
        :schema="schema"
        :error="errorMsg"
        @validate="onValidate"
        @submit="onSubmit"
      />
      <XButton
        type="primary"
        :disabled="invalidForm"
        @click="onSubmit"
      >Set Password</XButton>
    </div>
    <div
      v-else
      class="token-expired"
    >
      <div class="expired-text">
        Sorry, your token expired.
        Please contact your system administrator.
      </div>
    </div>
  </div>
</template>

<script>
import { validateResetPasswordToken, resetUserPasswordByToken } from '@api/user-tokens';
import XForm from '../../neurons/schema/Form.vue';
import XButton from '../../axons/inputs/Button.vue';
import { NOT_LOGGED_IN, SET_USER_ERROR } from '@store/modules/auth';
import { mapMutations } from 'vuex';
import { SHOW_TOASTER_MESSAGE } from '@store/mutations';

export default {
  name: 'XResetPasswordForm',
  components: {
    XForm, XButton,
  },
  props: {
    token: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      tokenStatus: {},
      errorMsg: '',
      credentials: {
        newPassword: '',
        confirmNewPassword: '',
      },
      invalidForm: true,
      items: [
        {
          name: 'newPassword', title: 'New password', type: 'string', format: 'password',
        },
        {
          name: 'confirmNewPassword', title: 'Confirm new password', type: 'string', format: 'password',
        },
      ],
      requiredItems: ['newPassword', 'confirmNewPassword'],
    };
  },
  computed: {
    schema() {
      return {
        type: 'array',
        required: this.requiredItems,
        items: this.items,
      };
    },
  },
  async created() {
    this.tokenStatus = await validateResetPasswordToken(this.token);
  },
  methods: {
    ...mapMutations({
      setUserError: SET_USER_ERROR,
      showToastMessage: SHOW_TOASTER_MESSAGE,

    }),
    onValidate(valid) {
      const confirmPasswordValue = this.credentials.confirmNewPassword;
      if (this.credentials.newPassword !== confirmPasswordValue && !!confirmPasswordValue) {
        this.errorMsg = 'Passwords do not match';
        this.invalidForm = true;
        return;
      }
      this.errorMsg = '';
      this.invalidForm = !valid;
    },
    async onSubmit() {
      const confirmPasswordValue = this.credentials.confirmNewPassword;
      if (!this.invalidForm) {
        try {
          await resetUserPasswordByToken(this.token, confirmPasswordValue);
          this.showToastMessage({ message: 'Password reset successfully' });
          this.setUserError({ error: NOT_LOGGED_IN });
          this.$router.push('/');
        } catch (e) {
          this.errorMsg = e.response.data.message;
          this.invalidForm = true;
        }
      }
    },
  },
};
</script>

<style lang="scss">
  .x-reset-password-form {

    .x-button {
      width: 100%;
      margin-top: 8px;
    }
    .token-expired {
      background: url('/src/assets/images/general/token_expired_bg.svg') no-repeat center center;
      font-family: Roboto, serif;
      height: 270px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding-bottom: 10px;
      .expired-text {
        font-size: 23px;
        line-height: 1.17;
        letter-spacing: 1px;
      }
    }
  }
</style>
