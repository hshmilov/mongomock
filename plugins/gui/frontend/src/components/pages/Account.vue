<template>
    <x-page title="My Account" class="x-account">
        <x-tabs>
            <x-tab title="Password" id="password-account-tab">
                <x-form :schema="passwordFormSchema" v-model="passwordForm" @validate="updatePasswordValidity"/>
                <div class="place-right">
                    <x-button :disabled="!passwordFormComplete" @click="savePassword">Save</x-button>
                </div>
            </x-tab>
            <x-tab title="API Key" id="apikey-account-tab" :selected="true">
                <x-button @click="openResetKeyModal">Reset Key</x-button>
                <div class="x-grid">
                    <label>API Key:</label>
                    <div>{{apiKey['api_key']}}</div>
                    <label>API Secret:</label>
                    <div>
                        <input type="text"
                                v-show="isKeyVisible"
                                class="secret-key visible"
                                :value="this.apiKey['api_secret']"
                                disabled/>
                        <input type="text"
                                v-show="!isKeyVisible"
                                class="secret-key invisible"
                                :value="invisibleSecretKey"
                                disabled/>

                        <md-button class="md-icon-button" @click="toggleVisibility">
                            <md-icon v-if="isKeyVisible" class="hide-key-icon" title="Hide API Secret">visibility_off</md-icon>
                            <md-icon v-else class="show-key-icon" title="Show API Secret">visibility</md-icon>
                        </md-button>
                        <md-button class="md-icon-button" @click="copyToClipboard">
                            <md-icon class="copy-to-clipboard-icon" title="Copy API Secret">filter_none</md-icon>
                        </md-button>
                    </div>

                </div>
            </x-tab>
        </x-tabs>
        <x-modal v-if="resetKeyActive" @close="closeResetKeyModal" @confirm="resetKey" approve-text="Reset Key"
                 approve-id="approve-reset-api-key">
            <div slot="body">
                Are you sure you want to revoke the current key and generate a new one?<br/>
                This means that all applications using this key will stop working.
            </div>
        </x-modal>
        <x-toast v-if="message" v-model="message" :timeout="6000"/>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTabs from '../axons/tabs/Tabs.vue'
    import xTab from '../axons/tabs/Tab.vue'
    import xForm from '../neurons/schema/Form.vue'
    import xButton from '../axons/inputs/Button.vue'
    import xModal from '../axons/popover/Modal.vue'
    import xToast from '../axons/popover/Toast.vue'

    import {CHANGE_PASSWORD} from '../../store/modules/auth'
    import {mapActions, mapMutations, mapState} from 'vuex'
    import {REQUEST_API} from '../../store/actions'
    import {SHOW_TOASTER_MESSAGE,} from '../../store/mutations'

    export default {
        name: 'x-account',
        components: {xPage, xTabs, xTab, xForm, xButton, xModal, xToast},
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
                isKeyVisible: false,
            }
        },
        computed: {
            ...mapState({
                userName(state) {
                    return state.auth.currentUser.data.user_name
                },
                userSource(state) {
                    return state.auth.currentUser.data.source
                }
            }),
            passwordFormSchema() {
                return {
                    type: 'array', 'items': [{
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
            },
            invisibleSecretKey() {
                return !this.apiKey['api_secret'] ? "" : this.apiKey['api_secret'].replace(/./gi, '*')
            }
        },
        methods: {
            ...mapActions({
                changePassword: CHANGE_PASSWORD,
                fetchData: REQUEST_API
            }),
            ...mapMutations({
                showToasterMessage: SHOW_TOASTER_MESSAGE
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
                if (this.passwordForm.newPassword !== this.passwordForm.confirmNewPassword) {
                    this.message = 'Passwords do not match'
                    return
                }
                this.changePassword({
                    oldPassword: this.passwordForm.currentPassword,
                    newPassword: this.passwordForm.newPassword
                }).then(() => {
                    this.message = 'Password changed'
                    this.passwordForm.currentPassword = null
                    this.passwordForm.newPassword = null
                    this.passwordForm.confirmNewPassword = null
                    this.passwordForm = {...this.passwordForm}
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
                        this.message = 'a new secret key has been generated, the old one is no longer valid'
                    }
                })
            },
            toggleVisibility() {
                this.isKeyVisible = !this.isKeyVisible
            },

            copyToClipboard() {
                const copySecretKey = document.getElementsByClassName('secret-key visible')[0];
                copySecretKey.select();
                navigator.clipboard.writeText(copySecretKey.value).then(
                    response => {
                        this.showToasterMessage({ message: 'Key was copied to Clipboard' })
                    },
                    error => {
                        this.showToasterMessage({ message : 'Key was not copied to Clipboard' })
                    }
                );
            }
        },
        created() {
            this.getApiKey()
        }
    }
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
            top: 10px;
            position: relative;
            background: transparent
        }
    }
</style>
