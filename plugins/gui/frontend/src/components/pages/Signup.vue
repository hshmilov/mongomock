<template>
    <div class="x-sign-up" v-if="showSignup">
        <x-page title="Sign up screen" class="x-account">
            <x-modal approve-text="Sign up" v-if="showSignup">
                <div slot="body">
                    Please fill the following details and click the save button
                    <div>
                        <x-form :schema="signupFormSchema" v-model="signupForm"/>
                    </div>
                    <div class="place-right">
                        <x-button id="signup-save" @click="onSave">Save</x-button>
                    </div>
                </div>
                <div slot="footer">
                </div>
            </x-modal>
            <x-toast v-if="message" :message="message" @done="removeToast" :timeout="6000"/>
        </x-page>
    </div>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xForm from '../neurons/schema/Form.vue'
    import xButton from '../axons/inputs/Button.vue'
    import xModal from '../axons/popover/Modal.vue'
    import xToast from '../axons/popover/Toast.vue'

    import {mapActions, mapState} from 'vuex'
    import {GET_SIGNUP, SUBMIT_SIGNUP} from "../../store/modules/auth";

    export default {
        name: 'x-signup',
        components: {xPage, xForm, xButton, xModal, xToast},
        data() {
            return {
                signupForm: {
                    companyName: null,
                    newPassword: null,
                    confirmNewPassword: null
                },
                message: ''
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
                },
                showSignup(state) {
                    return !state.auth.signup.data
                },
                signupFormSchema() {
                    return {
                        type: 'array', 'items': [
                            {
                                name: 'companyName',
                                title: 'Company name',
                                type: 'string',
                                format: 'string'
                            },
                            {
                                name: 'contactEmail',
                                title: 'Contact email',
                                type: 'string',
                                format: 'string'
                            },
                            {
                                name: 'newPassword',
                                title: 'Admin password',
                                type: 'string',
                                format: 'password'
                            },
                            {
                                name: 'confirmNewPassword',
                                title: 'Confirm admin password',
                                type: 'string',
                                format: 'password'
                            }],
                        required: ['companyName', 'newPassword', 'confirmNewPassword', 'contactEmail']
                    }
                }
            })
        },
        methods: {
            ...mapActions({
                submitSignup: SUBMIT_SIGNUP,
                getSignup: GET_SIGNUP
            }),
            onSave() {
                if (this.signupForm.newPassword !== this.signupForm.confirmNewPassword) {
                    this.message = 'Passwords do not match'
                    return
                }
                if (this.signupForm.newPassword === ''){
                    this.message = 'Empty password is not allowed'
                    return
                }
                this.submitSignup(
                    this.signupForm
                ).then(() => {
                    this.message = 'Signup completed'
                    this.signupForm = {...this.signupForm}
                    this.getSignup()
                }).catch(error => {
                    this.message = JSON.parse(error.request.response).message
                    this.getSignup()
                })
            },
            removeToast() {
                this.message = ''
            },
        },
        created() {
            this.getSignup()
        }
    }
</script>

<style lang="scss">
</style>
