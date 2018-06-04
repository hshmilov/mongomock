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
                <a @click="oktaclick" v-if="okta.enabled">Login with Okta</a> <br/>
                <a @click="ldapclick" v-if="ldap.enabled">Login with LDAP</a>
            </div>
        </div>
        <modal v-if="ldap_data.show_modal">
            <div slot="body">
                <div class="show-space">
                    <h2>Login with LDAP</h2>
                    <x-schema-form :schema="ldap_scheme" v-model="ldap_data.credentials" @input="initError" @validate="ldapUpdateValidity"
                               @submit="onLogin" :error="auth.error"/>
                    <button class="x-btn" :class="{disabled: !ldap_data.complete}" @click="onLdapLogin">Login</button>
                </div>
            </div>
            <div slot="footer">
                <button class="x-btn" @click="closeldap">Cancel</button>
            </div>
        </modal>
    </div>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import {LOGIN, INIT_ERROR, LDAP_LOGIN} from '../../store/modules/auth'
    import '../../components/icons/logo'
    import {mapState, mapMutations, mapActions} from 'vuex'
    import * as OktaAuth from '@okta/okta-auth-js';
    import Modal from '../../components/popover/Modal.vue'

    export default {
        name: 'login-container',
        components: {xSchemaForm, Modal},
        computed: {
            schema() {
                return {
                    type: 'array', items: [
                        {name: 'user_name', title: 'User Name', type: 'string'},
                        {name: 'password', title: 'Password', type: 'string', format: 'password'}
                    ], required: ['user_name', 'password']
                }
            },
            ldap_scheme() {
                return {
                        type: 'array',
                        items: [
                            {
                                name: 'user_name', title: 'User Name', type: 'string'
                            },
                            {
                                name: 'domain', title: 'Domain', type: 'string', default: this.ldap.default_domain
                            },
                            {
                                name: 'password', title: 'Password', type: 'string', format: 'password'
                            }
                        ], required: ['user_name', 'domain', 'password']
                    }
            },
            ...mapState(['auth'])
        },
        props: ['okta', 'ldap'],
        data() {
            return {
                credentials: {
                    user_name: '',
                    password: ''
                },
                complete: false,
                ldap_data: {
                    show_modal: false,
                    credentials: {
                        'user_name': '',
                        'domain': '',
                        'password': ''
                    },
                    complete: false,
                },
            }
        },
        methods: {
            ...mapMutations({initError: INIT_ERROR}),
            ...mapActions({login: LOGIN, ldap_login: LDAP_LOGIN}),
            updateValidity(valid) {
                this.complete = valid
            },
            ldapUpdateValidity(valid) {
                this.ldap_data.complete = valid
            },
            onLdapLogin(){
                if (!this.ldap_data.complete) return
                if (!this.ldap_data.credentials.domain)
                {
                    // workaround for default values not showing up
                    this.ldap_data.credentials.domain = this.ldap.default_domain
                }
                this.ldap_login(this.ldap_data.credentials)
            },
            onLogin() {
                if (!this.complete) return
                this.login(this.credentials)
            },
            oktaclick() {
                var x = new OktaAuth({
                    url: this.okta.url,
                    issuer: this.okta.url,
                    clientId: this.okta.client_id,
                    redirectUri: `${this.okta.gui_url}/api/okta-redirect`,
                    scope: 'openid'
                });
                x.token.getWithRedirect({ responseType: 'code' });
            },
            ldapclick() {
                this.ldap_data.show_modal = true
            },
            closeldap() {
                this.ldap_data.show_modal = false
            },
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