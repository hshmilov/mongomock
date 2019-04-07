<template>
  <div class="x-signup-form">
    <h3 class="title">Signup</h3>
    <div class="subtitle">Initial signup of your Axonius system</div>
    <x-form
      v-model="signupData"
      :schema="signupSchema"
      @validate="onValidate"
      @submit="onSave"
    />
    <x-button
      :disabled="!valid"
      @click="onSave"
    >Get Started</x-button>
    <x-toast
      v-if="message"
      v-model="message"
      :timeout="6000"
    />
  </div>
</template>

<script>
  import xForm from '../../neurons/schema/Form.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import xToast from '../../axons/popover/Toast.vue'

  import { mapActions } from 'vuex'
  import { SUBMIT_SIGNUP } from '../../../store/modules/auth'
  import { FETCH_SYSTEM_EXPIRED } from '../../../store/actions'

  export default {
    name: 'XSignupForm',
    components: {
      xForm, xButton, xToast
    },
    data() {
      return {
        signupData: {
          companyName: null,
          contactEmail: null,
          userName: 'admin',
          newPassword: null,
          confirmNewPassword: null
        },
        valid: false,
        message: ''
      }
    },
    computed: {
      signupSchema () {
        return {
          type: 'array', 'items': [{
              name: 'companyName',
              title: 'Your Organization',
              type: 'string',
            }, {
              name: 'contactEmail',
              title: 'Your Email',
              type: 'string',
            }, {
            name: 'userName',
            title: 'User Name',
            type: 'string',
            readOnly: true
          }, {
              name: 'newPassword',
              title: 'Set Password',
              type: 'string',
              format: 'password'
            }, {
              name: 'confirmNewPassword',
              title: 'Confirm Password',
              type: 'string',
              format: 'password'
            }],
          required: ['companyName', 'newPassword', 'confirmNewPassword', 'contactEmail', 'userName']
        }
      }
    },
    methods: {
      ...mapActions({
        submitSignup: SUBMIT_SIGNUP, fetchExpired: FETCH_SYSTEM_EXPIRED
      }),
      onValidate(valid) {
        this.valid = valid
      },
      onSave () {
        if (this.signupData.newPassword !== this.signupData.confirmNewPassword) {
          this.message = 'Passwords do not match'
          return
        }
        if (this.signupData.newPassword === '') {
          this.message = 'Empty password is not allowed'
          return
        }
        this.submitSignup(this.signupData).then(() => {
          this.message = 'Signup completed'
          this.$emit('done')
          this.fetchExpired()
        }).catch(error => {
          this.message = JSON.parse(error.request.response).message
          this.$emit('done')
        })
      }
    }
  }
</script>

<style lang="scss">
  .x-signup-form {
    height: 100%;
    .title {
      margin-bottom: 4px;
    }
    .subtitle {
      margin-bottom: 12px;
    }
  }
</style>