<template>
  <div class="x-login-options">
    <div
      v-if="oktaConfig.enabled || samlConfig.enabled || ldapConfig.enabled"
      class="t-center mt-12"
    >Or</div>
    <div class="options-buttons">
      <XButton
        v-if="oktaConfig.enabled"
        id="okta_login_link"
        :class="{'grid-span2': singleLoginMethod}"
        type="link"
        @click="onOktaLogin"
      >Login with Okta</XButton>
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
          :error="prettyUserError"
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
import { mapActions } from 'vuex';
import * as OktaAuth from '@okta/okta-auth-js';
import XForm from '../../neurons/schema/Form.vue';
import XButton from '../../axons/inputs/Button.vue';
import XModal from '../../axons/popover/Modal/index.vue';
import userErrorMixin from '../../../mixins/user_error';

import { LDAP_LOGIN } from '../../../store/modules/auth';

export default {
  name: 'XLoginOptions',
  components: {
    XForm, XButton, XModal,
  },
  mixins: [userErrorMixin],
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
      oktaConfig: {
        enabled: false,
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
      return (this.oktaConfig.enabled + this.samlConfig.enabled + this.ldapConfig.enabled) === 1;
    },
  },
  watch: {
    oktaConfig() {
      if (this.oktaConfig.enabled === true && this.$route.query.login_type === 'okta_login') {
        this.onOktaLogin();
      }
    },
    settings() {
      this.oktaConfig = this.settings.okta;
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
    onOktaLogin() {
      const gui2URL = this.oktaConfig.gui2_url.endsWith('/')
        ? this.oktaConfig.gui2_url.substr(0, this.oktaConfig.gui2_url.length - 1)
        : this.oktaConfig.gui2_url;
      const authorizationServer = this.oktaConfig.authorization_server
        ? `${this.oktaConfig.url}/oauth2/${this.oktaConfig.authorization_server}`
        : this.oktaConfig.url;
      const x = new OktaAuth({
        url: this.oktaConfig.url,
        issuer: authorizationServer,
        clientId: this.oktaConfig.client_id,
        redirectUri: `${gui2URL}/api/okta-redirect`,
      });
      x.token.getWithRedirect({
        scopes: ['openid', 'profile', 'email', 'offline_access'],
        responseType: 'code',
      });
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
