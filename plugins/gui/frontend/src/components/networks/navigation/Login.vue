<template>
    <div class="x-login" v-if="!auth.currentUser.data.user_name && !auth.currentUser.fetching">
        <div class="login-container">
            <div class="header">
                <svg-icon name="logo/logo" height="36" :original="true"></svg-icon>
                <svg-icon name="logo/axonius" height="20" :original="true" class="logo-subtext"></svg-icon>
            </div>
            <div class="body">
                <h3 class="title">Login</h3>
                <x-form :schema="schema" v-if="!staticConfiguration.medicalConfig" v-model="credentials" @input="initError"
                        @validate="onValidate" @submit="onLogin" :error="auth.currentUser.error"/>
                <button v-if="!staticConfiguration.medicalConfig" class="x-btn" :class="{disabled: !complete}" @click="onLogin">Login</button>
                <div v-if="(oktaConfig.enabled || samlConfig.enabled || ldapConfig.enabled) && !staticConfiguration.medicalConfig"
                     class="t-center mt-12">Or</div>
                <div class="login-options">
                    <a @click="onOktaLogin" v-if="oktaConfig.enabled" id="okta_login_link" class="x-btn link"
                       :class="{'grid-span2': singleLoginMethod}">Login with Okta</a>
                    <a @click="onSamlLogin" v-if="samlConfig.enabled" id="saml_login_link" class="x-btn link"
                       :class="{'grid-span2': singleLoginMethod}">Login with {{ samlConfig.idp_name }}</a>
                    <a @click="toggleLdapLogin" v-if="ldapConfig.enabled" id="ldap_login_link" class="x-btn link"
                       :class="{'grid-span2': singleLoginMethod}">Login with LDAP</a>
                </div>
            </div>
        </div>
        <x-modal v-if="ldapData.active" @close="toggleLdapLogin">
            <div slot="body">
                <div class="show-space">
                    <h2>Login with LDAP</h2>
                    <x-form :schema="ldapSchema" v-model="ldapData.credentials" @input="initError"
                            @validate="onValidateLDAP" @submit="onLdapLogin" :error="auth.currentUser.error"/>
                </div>
            </div>
            <div slot="footer">
                <button class="x-btn link" @click="toggleLdapLogin">Cancel</button>
                <button class="x-btn" :class="{disabled: !ldapData.complete}" @click="onLdapLogin">Login</button>
            </div>
        </x-modal>
    </div>
</template>

<script>
    import xForm from '../../neurons/schema/Form.vue'
    import xModal from '../../axons/popover/Modal.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {LOGIN, LDAP_LOGIN, INIT_ERROR, GET_LOGIN_OPTIONS} from '../../../store/modules/auth'
    import * as OktaAuth from '@okta/okta-auth-js'

    export default {
        name: 'x-login',
        components: {xForm, xModal},
        watch: {
            oktaConfig() {
                if (this.oktaConfig.enabled === true && this.$route.query.login_type === 'okta_login') {
                    this.onOktaLogin()
                }
            }
        },
        computed: {
            ...mapState(['auth', 'staticConfiguration']),
            schema() {
                return {
                    type: 'array', items: [
                        {name: 'user_name', title: 'User Name', type: 'string'},
                        {name: 'password', title: 'Password', type: 'string', format: 'password'},
                        {name: 'remember_me', title: 'Remember me', type: 'bool', default: false}
                    ], required: ['user_name', 'password']
                }
            },
            ldapSchema() {
                return {
                    type: 'array',
                    items: [
                        {name: 'user_name', title: 'User Name', type: 'string'},
                        {name: 'domain', title: 'Domain', type: 'string', default: this.ldapConfig.default_domain},
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
        data() {
            return {
                credentials: {
                    user_name: '',
                    password: '',
                    remember_me: false
                },
                complete: false,
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
        methods: {
            ...mapMutations({initError: INIT_ERROR}),
            ...mapActions({getLoginSettings: GET_LOGIN_OPTIONS, login: LOGIN, ldapLogin: LDAP_LOGIN}),
            onValidate(valid) {
                this.complete = valid
            },
            onValidateLDAP(valid) {
                this.ldapData.complete = valid
            },
            onLdapLogin() {
                if (!this.ldapData.complete) return
                if (!this.ldapData.credentials.domain) {
                    // workaround for default values not showing up
                    this.ldapData.credentials.domain = this.ldapConfig.default_domain
                }
                this.ldapLogin(this.ldapData.credentials)
            },
            onLogin() {
                if (!this.complete) return
                this.login(this.credentials)
            },
            onOktaLogin() {
                let gui2URL = this.oktaConfig.gui2_url.endsWith('/') ?
                    this.oktaConfig.gui2_url.substr(0, this.oktaConfig.gui2_url.length - 1)
                    :
                    this.oktaConfig.gui2_url
                let x = new OktaAuth({
                    url: this.oktaConfig.url,
                    issuer: this.oktaConfig.url,
                    clientId: this.oktaConfig.client_id,
                    redirectUri: `${gui2URL}/api/okta-redirect`,
                    scope: 'openid'
                })
                x.token.getWithRedirect({responseType: 'code'})
            },
            onSamlLogin() {
                window.location.href = '/api/login/saml'
            },
            toggleLdapLogin() {
                this.ldapData.active = !this.ldapData.active
            }
        },
        created() {
            this.getLoginSettings().then(response => {
                if (response.status === 200) {
                    this.oktaConfig = response.data.okta
                    this.samlConfig = response.data.saml
                    this.ldapConfig = response.data.ldap
                }
            })
        }
    }
</script>

<style lang="scss">
    .x-login {
        background: url('/src/assets/images/general/login_bg.png');
        background-size: cover;
        background-position: center bottom;
        height: 100vh;
        padding-top: 20vh;

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

            .body {
                background-color: white;
                flex: 1 0 auto;
                padding: 48px;
                border-radius: 4px;

                .title {
                    margin-top: 0;
                }

                .x-form {
                    .array {
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

                .x-btn {
                    width: 100%;
                }

                .login-options {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    grid-gap: 12px 0;

                    .x-btn.link {
                        width: auto;
                    }

                    .abcRioButton {
                        margin: auto;
                    }
                }
            }

        }
    }
</style>
