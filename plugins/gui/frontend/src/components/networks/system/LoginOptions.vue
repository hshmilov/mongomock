<template>
  <div class="x-login-options">
    <div
      v-if="samlConfig.enabled || ldapConfig.enabled"
      class="t-center mt-12"
    >Or</div>
    <div class="options-buttons">
      <XButton
        v-if="samlConfig.enabled"
        id="saml_login_link"
        :class="{'grid-span2': singleLoginMethod}"
        type="link"
        @click="onSamlLogin"
      >Login with {{ samlConfig.idp_name }}</XButton>
      <XButton
        v-if="ldapConfig.enabled"
        id="ldap_login_link"
        :class="{'grid-span2': singleLoginMethod}"
        type="link"
        @click="toggleLdapLogin"
      >Login with LDAP</XButton>
    </div>
    <XModal
      v-if="ldapData.active"
      size="md"
      @close="toggleLdapLogin"
    >
      <div slot="body">
        <h2>Login with LDAP</h2>
        <XForm
          v-model="ldapData.credentials"
          :schema="ldapSchema"
          :error="userError"
          @validate="onValidateLDAP"
          @submit="onLdapLogin"
        />
      </div>
      <div slot="footer">
        <XButton
          type="link"
          @click="toggleLdapLogin"
        >Cancel</XButton>
        <XButton
          type="primary"
          :disabled="!ldapData.complete"
          @click="onLdapLogin"
        >Login</XButton>
      </div>
    </XModal>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import XForm from '../../neurons/schema/Form.vue';
import XButton from '../../axons/inputs/Button.vue';
import XModal from '../../axons/popover/Modal/index.vue';

import { LDAP_LOGIN } from '../../../store/modules/auth';

export default {
  name: 'XLoginOptions',
  components: {
    XForm, XButton, XModal,
  },
  props: {
    settings: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      ldapData: {
        active: false,
        credentials: {
          user_name: '',
          domain: '',
          password: '',
        },
        complete: false,
      },
      samlConfig: {
        enabled: false,
      },
      ldapConfig: {
        enabled: false,
      },
    };
  },
  computed: {
    ...mapState({
      userError(state) {
        return state.auth.currentUser.error;
      },
    }),
    ldapSchema() {
      return {
        type: 'array',
        items: [
          { name: 'user_name', title: 'User Name', type: 'string' },
          {
            name: 'password', title: 'Password', type: 'string', format: 'password',
          },
          { name: 'domain', title: 'Domain', type: 'string' },
        ],
        required: ['user_name', 'domain', 'password'],
      };
    },
    singleLoginMethod() {
      return (this.samlConfig.enabled + this.ldapConfig.enabled) === 1;
    },
  },
  watch: {
    settings() {
      this.samlConfig = this.settings.saml;
      this.ldapConfig = this.settings.ldap;
      if (this.ldapConfig.default_domain) {
        this.ldapData.credentials.domain = this.ldapConfig.default_domain;
      }
    },
  },
  methods: {
    ...mapActions({ ldapLogin: LDAP_LOGIN }),
    onValidateLDAP(valid) {
      this.ldapData.complete = valid;
    },
    onLdapLogin() {
      this.ldapLogin(this.ldapData.credentials);
    },
    onSamlLogin() {
      window.location.href = '/api/login/saml';
    },
    toggleLdapLogin() {
      this.ldapData.active = !this.ldapData.active;
    },
  },
};
</script>

<style lang="scss">
  .x-login-options {

    .options-buttons {
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-gap: 12px 0;

    }
  }
</style>
