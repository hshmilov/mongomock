<template>
    <x-page title="My Account" class="account">
        <tabs>
            <tab title="Password" id="password-account-tab">
                <x-schema-form :schema="passwordFormSchema" v-model="passwordForm" @validate="updatePasswordValidity"/>
                <div class="place-right">
                    <button class="x-btn" :class="{disabled: !passwordFormComplete}" @click="savePassword">Save</button>
                </div>
            </tab>
            <tab title="API Key" id="apikey-account-tab" :selected="true">
                <button class="x-btn" @click="openResetKeyModal">Reset Key</button>
                <div class="x-grid">
                    <label>API Key:</label>
                    <div>{{apiKey['api_key']}}</div>
                    <label>API secret:</label>
                    <div>{{apiKey['api_secret']}}</div>
                </div>
            </tab>
        </tabs>
        <modal v-if="resetKeyActive" @close="closeResetKeyModal" @confirm="resetKey" approve-text="Reset Key" approve-id="approve-reset-api-key">
            <div slot="body">
                Are you sure you want to revoke the current key and generate a new one?<br/>
                This means that all applications using this key will stop working.
            </div>
        </modal>
        <x-toast v-if="message" :message="message" @done="removeToast" :timeout="6000" />
    </x-page>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import xPage from '../../components/layout/Page.vue'
    import {CHANGE_PASSWORD} from "../../store/modules/auth";
    import {mapActions, mapState} from 'vuex'
    import xToast from '../../components/popover/Toast.vue'
    import Tabs from '../../components/tabs/Tabs.vue'
    import Tab from '../../components/tabs/Tab.vue'
    import Modal from '../../components/popover/Modal.vue'
    import {REQUEST_API} from "../../store/actions";

    export default {
        name: 'my-account',
        components: {xToast, xPage, xSchemaForm, Tabs, Tab, Modal},
        data() {
            return {
                passwordForm: {
                    currentPassword: null,
                    newPassword: null,
                    confirmNewPassword: null
                },
                passwordFormComplete: false,
                message: '',
                apiKey: {},
                resetKeyActive: false,
            }
        },
        computed: {
            ...mapState({
                userName(state) {
                    return state.auth.currentUser.data.user_name
                },
                userSource(state) {
                    return state.auth.currentUser.data.source
                },
                userId(state) {
                    return state.auth.currentUser.data.uuid
                }
            }),
            passwordFormSchema() {
                return {
                    type:'array', 'items': [{
                        name: 'currentPassword',
                        title: 'Current password',
                        type: 'string',
                        format: 'password'
                    }, {
                        name: 'newPassword',
                        title: 'New password',
                        type: 'string',
                        format: 'password'
                    }, {
                        name: 'confirmNewPassword',
                        title: 'Confirm new password',
                        type: 'string',
                        format: 'password'
                    }], required: ['currentPassword', 'newPassword', 'confirmNewPassword']
                }
            }
        },
        methods: {
            ...mapActions({
                changePassword: CHANGE_PASSWORD,
                fetchData: REQUEST_API,
            }),
            updatePasswordValidity(valid) {
                this.passwordFormComplete = valid
            },
            openResetKeyModal() {
                this.resetKeyActive = true
            },
            closeResetKeyModal() {
                this.resetKeyActive = false
            },
            savePassword() {
                if (!this.passwordFormComplete) return
                if (this.passwordForm.newPassword !== this.passwordForm.confirmNewPassword) {
                    this.message = "Passwords don't match"
                    return
                }
                this.changePassword({
                    uuid: this.userId,
                    oldPassword: this.passwordForm.currentPassword,
                    newPassword: this.passwordForm.newPassword
                }).then(() => {
                    this.message = "Password changed"
                    this.passwordForm.currentPassword = null
                    this.passwordForm.newPassword = null
                    this.passwordForm.confirmNewPassword = null
                    this.passwordForm = { ...this.passwordForm }
                }).catch(error => {
                    this.message = JSON.parse(error.request.response).message
                })
            },
            getApiKey() {
                this.fetchData({
                    rule: 'api_key'
                }).then(response => {
                    if (response.status === 200 && response.data) {
                        this.apiKey = response.data
                    }
                })
            },
            resetKey() {
                this.closeResetKeyModal()
                this.fetchData({
                    rule: 'api_key',
                    method: 'POST'
                }).then(response => {
                    if (response.status === 200 && response.data) {
                        this.apiKey = response.data
                        this.message = "a new secret key has been generated, the old one is no longer valid"
                    }
                })
            },
            removeToast() {
                this.message = ''
            },

        },
        created() {
            this.getApiKey()
        }
    }
</script>

<style lang="scss">
    .account {
        .x-tabs {
            max-width: 840px;
        }
        .password-account-tab {
            .schema-form .array {
                grid-template-columns: 1fr;
            }
        }
        .apikey-account-tab {
            .x-btn {
                margin-top: 12px;
            }
            .x-grid {
                margin-top: 24px;
                grid-template-columns: 1fr 2fr;
            }
        }
    }
</style>
