<template>
  <XPage
    title="My Account"
    class="x-account"
  >
    <XTabs>
      <XTab
        id="password-account-tab"
        title="Password"
      >
        <XForm
          v-model="passwordForm"
          :schema="passwordFormSchema"
          @validate="updatePasswordValidity"
        />
        <div class="place-right">
          <XButton
            :disabled="!passwordFormComplete"
            @click="savePassword"
          >
            Save
          </XButton>
        </div>
      </XTab>
      <XTab
        id="apikey-account-tab"
        title="API Key"
        :selected="true"
      >
        <XButton @click="openResetKeyModal">
          Reset Key
        </XButton>
        <div class="x-grid">
          <label>API Key:</label>
          <div>{{ apiKey['api_key'] }}</div>
          <label>API Secret:</label>
          <div>
            <input
              v-show="isKeyVisible"
              type="text"
              class="secret-key visible"
              :value="this.apiKey['api_secret']"
              disabled
            >
            <input
              v-show="!isKeyVisible"
              type="text"
              class="secret-key invisible"
              :value="invisibleSecretKey"
              disabled
            >

            <AButton
              v-if="isKeyVisible"
              class="hide-key-icon"
              title="Hide API Secret"
              shape="circle"
              @click="toggleVisibility"
              icon="eye-invisible"
            />
            <AButton
              v-else
              class="show-key-icon"
              title="Show API Secret"
              shape="circle"
              @click="toggleVisibility"
              icon="eye"
            />
            <AButton
              class="copy-to-clipboard-icon"
              title="Copy API Secret"
              shape="circle"
              icon="copy"
              @click="copyToClipboard"
            />
          </div>

        </div>
      </XTab>
    </XTabs>
    <XModal
      v-if="resetKeyActive"
      approve-text="Reset Key"
      approve-id="approve-reset-api-key"
      @close="closeResetKeyModal"
      @confirm="resetKey"
    >
      <div slot="body">
        Are you sure you want to revoke the current key and generate a new one?<br>
        This means that all applications using this key will stop working.
      </div>
    </XModal>
    <XToast
      v-if="message"
      v-model="message"
      :timeout="6000"
    />
  </XPage>
</template>

<script>
import { mapActions, mapMutations, mapState } from 'vuex';
import XPage from '../axons/layout/Page.vue';
import XTabs from '../axons/tabs/Tabs.vue';
import XTab from '../axons/tabs/Tab.vue';
import XForm from '../neurons/schema/Form.vue';
import XButton from '../axons/inputs/Button.vue';
import XModal from '../axons/popover/Modal/index.vue';
import XToast from '../axons/popover/Toast.vue';

import { CHANGE_PASSWORD } from '../../store/modules/auth';
import { REQUEST_API } from '../../store/actions';
import { SHOW_TOASTER_MESSAGE } from '../../store/mutations';

export default {
  name: 'XAccount',
  components: {
    XPage, XTabs, XTab, XForm, XButton, XModal, XToast,
  },
  data() {
    return {
      passwordForm: {
        currentPassword: null,
        newPassword: null,
        confirmNewPassword: null,
      },
      passwordFormComplete: false,
      message: '',
      apiKey: {},
      resetKeyActive: false,
      isKeyVisible: false,
    };
  },
  computed: {
    ...mapState({
      userName(state) {
        return state.auth.currentUser.data.user_name;
      },
      userSource(state) {
        return state.auth.currentUser.data.source;
      },
    }),
    passwordFormSchema() {
      return {
        type: 'array',
        items: [{
          name: 'currentPassword',
          title: 'Current password',
          type: 'string',
          format: 'password',
        }, {
          name: 'newPassword',
          title: 'New password',
          type: 'string',
          format: 'password',
        }, {
          name: 'confirmNewPassword',
          title: 'Confirm new password',
          type: 'string',
          format: 'password',
        }],
        required: ['currentPassword', 'newPassword', 'confirmNewPassword'],
      };
    },
    invisibleSecretKey() {
      return !this.apiKey.api_secret ? '' : this.apiKey.api_secret.replace(/./gi, '*');
    },
  },
  methods: {
    ...mapActions({
      changePassword: CHANGE_PASSWORD,
      fetchData: REQUEST_API,
    }),
    ...mapMutations({
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    updatePasswordValidity(valid) {
      this.passwordFormComplete = valid;
    },
    openResetKeyModal() {
      this.resetKeyActive = true;
    },
    closeResetKeyModal() {
      this.resetKeyActive = false;
    },
    savePassword() {
      if (this.passwordForm.newPassword !== this.passwordForm.confirmNewPassword) {
        this.message = 'Passwords do not match';
        return;
      }
      this.changePassword({
        oldPassword: this.passwordForm.currentPassword,
        newPassword: this.passwordForm.newPassword,
      }).then(() => {
        this.message = 'Password changed';
        this.passwordForm.currentPassword = null;
        this.passwordForm.newPassword = null;
        this.passwordForm.confirmNewPassword = null;
        this.passwordForm = { ...this.passwordForm };
      }).catch((error) => {
        this.message = JSON.parse(error.request.response).message;
      });
    },
    getApiKey() {
      this.fetchData({
        rule: 'api_key',
      }).then((response) => {
        if (response.status === 200 && response.data) {
          this.apiKey = response.data;
        }
      });
    },
    resetKey() {
      this.closeResetKeyModal();
      this.fetchData({
        rule: 'api_key',
        method: 'POST',
      }).then((response) => {
        if (response.status === 200 && response.data) {
          this.apiKey = response.data;
          this.message = 'a new secret key has been generated, the old one is no longer valid';
        }
      });
    },
    toggleVisibility() {
      this.isKeyVisible = !this.isKeyVisible;
    },

    copyToClipboard() {
      const copySecretKey = document.getElementsByClassName('secret-key visible')[0];
      copySecretKey.select();
      navigator.clipboard.writeText(copySecretKey.value).then(
        (response) => {
          this.showToasterMessage({ message: 'Key was copied to Clipboard' });
        },
        (error) => {
          this.showToasterMessage({ message: 'Key was not copied to Clipboard' });
        },
      );
    },
  },
  created() {
    this.getApiKey();
  },
};
</script>

<style lang="scss">
    .x-account {
        .x-tabs {
            max-width: 840px;
        }

        .password-account-tab {
            .x-form .x-array-edit {
                grid-template-columns: 1fr;
            }
        }

        .apikey-account-tab {
            .x-button {
                margin-top: 12px;
            }

            .x-grid {
                margin-top: 24px;
                grid-template-columns: 1fr 2fr;
            }
        }
        .md-icon-button {
            color: $theme-blue
        }
        .secret-key {
            width: 360px;
            border: none;
            position: relative;
            background: transparent
        }

        .ant-btn-icon-only {
            margin: 0 3px;
        }
    }
</style>
