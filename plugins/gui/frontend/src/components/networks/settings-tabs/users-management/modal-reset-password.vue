<template>
  <XModal
    :dismissable="true"
    @close="onCloseModal"
  >
    <div slot="body">
      <div
        v-if="!link"
        class="v-spinner-bg"
      />
      <PulseLoader
        :loading="!link"
        color="#FF7D46"
      />
      <div class="reset-password__form">
        <!-- password reset link -->
        <div class="item form__name">
          <h5>Password reset link has been generated </h5> (valid for {{ validForHours }} hours)
          <input
            v-model="link"
            class="reset-link__input"
            disabled
          >
          <XButton
            type="primary"
            class="copy-to-clipboard-icon"
            title="Copy Reset Link"
            shape="circle"
            icon="copy"
            @click="copyToClipboard"
          />
        </div>

        <!-- email -->
        <div class="item form__first-name">
          <h5>Email reset password link to:</h5>
          <input
            v-model="$v.email.$model"
            :disabled="!canSendEmail"
            placeholder="Enter Email"
            class="email__input"
          >
          <p
            v-if="$v.email.$error"
            class="error-input indicator-error--text"
          >Please enter a valid email address to send the reset token</p>
        </div>
        <div
          v-if="!canSendEmail"
          class="no-email-server"
        >
          <AIcon type="bulb" />
          You can send the password reset link by email
          after configuring an Email server in the Global Settings
        </div>
      </div>
    </div>
    <div slot="footer">
      <p
        v-if="serverError"
        class="error-input indicator-error--text"
      >{{ serverError }}</p>
      <XButton
        type="primary"
        :loading="sendingEmail"
        :disabled="!canSendEmail || this.$v.$invalid"
        @click="sendEmail"
      >Send Email</XButton>
    </div>
  </XModal>
</template>

<script>
import { email, required } from 'vuelidate/lib/validators';
import PulseLoader from 'vue-spinner/src/PulseLoader.vue';
import _get from 'lodash/get';
import copy from 'copy-to-clipboard';
import { Icon } from 'ant-design-vue';
import { mapMutations, mapState } from 'vuex';

import XModal from '@axons/popover/Modal/index.vue';
import XButton from '@axons/inputs/Button.vue';
import { getUserResetPasswordLink, sendResetPasswordTokenEmail } from '@api/user-tokens';
import { SHOW_TOASTER_MESSAGE } from '@store/mutations';

export default {
  name: 'XModalResetPassword',
  components: {
    XModal,
    XButton,
    PulseLoader,
    AIcon: Icon,
  },
  props: {
    userId: {
      type: String,
      default: '',
    },
    userEmail: {
      type: String,
      default: '',
    },
    invite: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      link: '',
      email: '',
      sendingEmail: false,
      serverError: null,
    };
  },
  validations: {
    email: { email, required },
  },
  computed: {
    ...mapState({
      coreSettings(state) {
        return _get(state, 'settings.configurable.core.CoreService', undefined);
      },
    }),
    canSendEmail() {
      return _get(this.coreSettings, 'config.email_settings.enabled', false);
    },
    validForHours() {
      return _get(this.coreSettings, 'config.password_reset_password.reset_password_link_expiration', 48);
    },
  },
  async created() {
    this.link = await getUserResetPasswordLink(this.userId, this.invite);
    this.email = this.userEmail;
  },
  async mounted() {
    this.link = await getUserResetPasswordLink(this.userId, this.invite);
    this.email = this.userEmail;
  },
  methods: {
    ...mapMutations({
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    onCloseModal() {
      this.$emit('close');
    },
    copyToClipboard() {
      try {
        copy(this.link);
        this.showToasterMessage({ message: 'Password link was copied to Clipboard' });
      } catch (e) {
        this.showToasterMessage({ message: 'Password link was not copied to Clipboard' });
      }
    },
    async sendEmail() {
      this.$v.$touch();
      if (this.$v.$invalid) {
        return;
      }
      this.sendingEmail = true;
      try {
        await sendResetPasswordTokenEmail(this.userId, this.email, this.invite);
        this.showToasterMessage({ message: 'Password link was sent successfully' });
        this.serverError = null;
      } catch (e) {
        this.serverError = e.response.data.message;
      }
      this.sendingEmail = false;
    },
  },
};
</script>

<style lang="scss">
  .x-users-management {
    .x-modal {
      z-index: 1004;
      .v-spinner-bg {
        left: 0;
      }
      .v-spinner {
        top: 0;
        left: 0;
      }
      .modal-header {
        padding: 0;
      }
      .reset-password__form {
        h5 {
          display: inline;
          font-size: 16px;
          font-weight: 400;
          color: $theme-black;
          margin: 0 0 3px 0;
        }

        input {
          width: 680px;
          height: 30px;
          padding: 4px;
          display: inline-block;

        }

        .item {
          margin: 0 0 16px 0;
        }
        .no-email-server {
          font-size: 13px;
        }
      }
    }

  }
</style>
