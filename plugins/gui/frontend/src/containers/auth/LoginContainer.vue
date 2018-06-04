<template>
    <div class="login-container" v-if="!auth.data.user_name && !auth.fetching">
        <div class="login">
            <div class="header">
                <svg-icon name="logo/logo" height="36" :original="true"></svg-icon>
                <svg-icon name="logo/axonius" height="20" :original="true" class="logo-subtext"></svg-icon>
            </div>
            <div class="body">
                <h3 class="title">Login</h3>
                <x-schema-form :schema="schema" v-model="credentials" @input="initError" @validate="updateValidity"
                               @submit="onLogin" :error="auth.error"/>
                <button class="x-btn" :class="{disabled: !complete}" @click="onLogin">Login</button>
                <a @click="onOktaLogin" v-if="oktaConfig.enabled" class="link">Login with Okta</a>
                <a @click="toggleLdapLogin" v-if="ldapConfig.enabled" class="link">Login with LDAP</a>
            </div>
        </div>
        <modal v-if="ldapData.active" @close="toggleLdapLogin">
            <div slot="body">
                <div class="show-space">
                    <h2>Login with LDAP</h2>
                    <x-schema-form :schema="ldapSchema" v-model="ldapData.credentials" @input="initError"
                                   @validate="ldapUpdateValidity" @submit="onLdapLogin" :error="auth.error"/>
                </div>
            </div>
            <div slot="footer">
                <button class="x-btn link" @click="toggleLdapLogin">Cancel</button>
                <button class="x-btn" :class="{disabled: !ldapData.complete}" @click="onLdapLogin">Login</button>
            </div>
        </modal>
    </div>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import Modal from '../../components/popover/Modal.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
    import { LOGIN, LDAP_LOGIN, INIT_ERROR, GET_LOGIN_OPTIONS } from '../../store/modules/auth'
    import * as OktaAuth from '@okta/okta-auth-js';

    export default {
        name: 'login-container',
        components: { xSchemaForm, Modal },
        computed: {
            schema() {
                return {
                    type: 'array', items: [
                        {name: 'user_name', title: 'User Name', type: 'string'},
                        {name: 'password', title: 'Password', type: 'string', format: 'password'}
                    ], required: ['user_name', 'password']
                }
            },
            ldapSchema() {
                return {
                    type: 'array',
                    items: [
                        {
                            name: 'user_name', title: 'User Name', type: 'string'
                        },
                        {
                            name: 'domain', title: 'Domain', type: 'string', default: this.ldapConfig.default_domain
                        },
                        {
                            name: 'password', title: 'Password', type: 'string', format: 'password'
                        }
                    ], required: ['user_name', 'domain', 'password']
                    }
            },
            ...mapState(['auth'])
        },
        data() {
            return {
                credentials: {
                    user_name: '',
                    password: ''
                },
                complete: false,
                ldapData: {
                    active: false,
                    credentials: {
                        'user_name': '',
                        'domain': '',
                        'password': ''
                    },
                    complete: false,
                },
                oktaConfig: {
                    enabled: false
                },
                ldapConfig: {
					enabled: false
                }
            }
        },
        methods: {
            ...mapMutations({ initError: INIT_ERROR }),
            ...mapActions({ getLoginSettings: GET_LOGIN_OPTIONS, login: LOGIN, ldapLogin: LDAP_LOGIN}),
            updateValidity(valid) {
                this.complete = valid
            },
            ldapUpdateValidity(valid) {
                this.ldapData.complete = valid
            },
            onLdapLogin(){
                if (!this.ldapData.complete) return
                if (!this.ldapData.credentials.domain)
                {
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
                var x = new OktaAuth({
					url: this.oktaConfig.url,
					issuer: this.oktaConfig.url,
					clientId: this.oktaConfig.client_id,
					redirectUri: `${this.oktaConfig.gui_url}/api/okta-redirect`,
					scope: 'openid'
				});
				x.token.getWithRedirect({ responseType: 'code' })
			},
			toggleLdapLogin() {
				this.ldapData.active = !this.ldapData.active
			}
        },
        created() {
            this.getLoginSettings().then(response => {
                if (response.status === 200) {
                    this.oktaConfig = response.data.okta
                    this.ldapConfig = response.data.ldap
                }
            })
        }
    }
</script>

<style lang="scss">
    .login-container {
        background: url('/src/assets/images/general/login_bg.png') center;
        height: 100vh;
        padding-top: 20vh;
        .login {
            width: 30vw;
            min-width: 300px;
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
                .schema-form {
                    .array {
                        display: block;
                        .object {
                            width: 100%;
                        }
                        .item {
                            width: 100%;
                        }
                    }
                }
                .x-btn {
                    width: 100%;
                }
            }

        }
    }
</style>