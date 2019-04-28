<template>
  <div class="x-login-options">
    <div
      v-if="oktaConfig.enabled || samlConfig.enabled || ldapConfig.enabled"
      class="t-center mt-12"
    >Or</div>
    <div class="options-buttons">
      <x-button
        v-if="oktaConfig.enabled"
        id="okta_login_link"
        :class="{'grid-span2': singleLoginMethod}"
        link
        @click="onOktaLogin"
      >Login with Okta</x-button>
      <x-button
        v-if="samlConfig.enabled"
        id="saml_login_link"
        :class="{'grid-span2': singleLoginMethod}"
        link
        @click="onSamlLogin"
      >Login with {{ samlConfig.idp_name }}</x-button>
      <x-button
        v-if="ldapConfig.enabled"
        id="ldap_login_link"
        :class="{'grid-span2': singleLoginMethod}"
        link
        @click="toggleLdapLogin"
      >Login with LDAP</x-button>
    </div>
    <x-modal
      v-if="ldapData.active"
      @close="toggleLdapLogin"
    >
      <div slot="body" class="show-space">
        <h2>Login with LDAP</h2>
        <x-form
          v-model="ldapData.credentials"
          :schema="ldapSchema"
          :error="prettyUserError"
          @input="initError"
          @validate="onValidateLDAP"
          @submit="onLdapLogin"
        />
      </div>
      <div slot="footer">
        <x-button
          link
          @click="toggleLdapLogin"
        >Cancel</x-button>
        <x-button
          :disabled="!ldapData.complete"
          @click="onLdapLogin"
        >Login</x-button>
      </div>
    </x-modal>
  </div>
</template>

<script>
  import xForm from '../../neurons/schema/Form.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import xModal from '../../axons/popover/Modal.vue'
  import userErrorMixin from '../../../mixins/user_error'

  import {mapActions} from 'vuex'
  import {LDAP_LOGIN, GET_LOGIN_OPTIONS} from '../../../store/modules/auth'
  import * as OktaAuth from '@okta/okta-auth-js'

  export default {
    name: 'XLoginOptions',
    components: {
      xForm, xButton, xModal
    },
    mixins: [userErrorMixin],
    props: {
      loginOkta: {
        type: Boolean,
        default: false
      }
    },
    data() {
      return {
        ldapData: {
          active: false,
          credentials: {
            'user_name': '',
            'domain': '',
            'password': ''
          },
          complete: false
        },
        oktaConfig: {
          enabled: false
        },
        samlConfig: {
          enabled: false
        },
        ldapConfig: {
          enabled: false
        }
      }
    },
    computed: {
      ldapSchema() {
        return {
          type: 'array',
          items: [
            {name: 'user_name', title: 'User Name', type: 'string'},
            {name: 'domain', title: 'Domain', type: 'string'},
            {
              name: 'password', title: 'Password', type: 'string', format: 'password'
            }
          ], required: ['user_name', 'domain', 'password']
        }
      },
      singleLoginMethod() {
        return (this.oktaConfig.enabled + this.samlConfig.enabled + this.ldapConfig.enabled) === 1
      }
    },
    watch: {
      oktaConfig () {
        if (this.oktaConfig.enabled === true && this.$route.query.login_type === 'okta_login') {
          this.onOktaLogin()
        }
      }
    },
    mounted() {
      this.getLoginSettings().then(response => {
        if (response.status === 200) {
          this.oktaConfig = response.data.okta
          this.samlConfig = response.data.saml
          this.ldapConfig = response.data.ldap
          if (this.ldapConfig.default_domain) {
            this.ldapData.credentials.domain = this.ldapConfig.default_domain
          }
          if (this.loginOkta) {
            this.onOktaLogin()
          }
        }
      })
    },
    methods: {
      ...mapActions({ getLoginSettings: GET_LOGIN_OPTIONS, ldapLogin: LDAP_LOGIN }),
      onValidateLDAP (valid) {
        this.ldapData.complete = valid
      },
      onLdapLogin () {
        this.ldapLogin(this.ldapData.credentials)
      },
      onOktaLogin () {
        let gui2URL = this.oktaConfig.gui2_url.endsWith('/') ?
          this.oktaConfig.gui2_url.substr(0, this.oktaConfig.gui2_url.length - 1)
          :
          this.oktaConfig.gui2_url
        let authorization_server = this.oktaConfig.authorization_server ?
          `${this.oktaConfig.url}/oauth2/${this.oktaConfig.authorization_server}`
          :
          this.oktaConfig.url
        let x = new OktaAuth({
          url: this.oktaConfig.url,
          issuer: authorization_server,
          clientId: this.oktaConfig.client_id,
          redirectUri: `${gui2URL}/api/okta-redirect`
        })
        x.token.getWithRedirect({
          scopes: ['openid', 'profile', 'email', 'offline_access'],
          responseType: 'code'
        })
      },
      onSamlLogin () {
        window.location.href = '/api/login/saml'
      },
      toggleLdapLogin () {
        this.ldapData.active = !this.ldapData.active
      }
    }
  }
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