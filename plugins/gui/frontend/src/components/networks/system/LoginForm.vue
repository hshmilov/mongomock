<template>
  <div class="x-login-form">
    <h3 class="login-title">Login</h3>
    <x-form
      v-model="credentials"
      :schema="schema"
      :error="prettyUserError"
      @validate="onValidate"
      @submit="onLogin"/>
    <x-button
      :disabled="!complete"
      @click="onLogin"
    >Login</x-button>
  </div>
</template>

<script>
  import xForm from '../../neurons/schema/Form.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import userErrorMixin from '../../../mixins/user_error'
  import { GettingStartedPubSub } from '../../App.vue'

  import {mapActions} from 'vuex'
  import {LOGIN} from '../../../store/modules/auth'

  export default {
    name: 'XLoginForm',
    components: {
      xForm, xButton
    },
    mixins: [userErrorMixin],
    data() {
      return {
        credentials: {
          user_name: '',
          password: '',
          remember_me: false
        },
        complete: false
      }
    },
    computed: {
      schema() {
        return {
          type: 'array', items: [
            {name: 'user_name', title: 'User Name', type: 'string'},
            {name: 'password', title: 'Password', type: 'string', format: 'password'},
            {name: 'remember_me', title: 'Remember me', type: 'bool', default: false}
          ], required: ['user_name', 'password']
        }
      }
    },
    methods: {
      ...mapActions({ login: LOGIN }),
      onValidate (valid) {
        this.complete = valid
      },
      onLogin () {
        this.login(this.credentials).then(res => {
          // Set getting started panel state to open=true
          if (res.status == 200) {
            GettingStartedPubSub.$emit('getting-started-login')
          }
        })
      }
    }
  }
</script>

<style lang="scss">
  .x-login-form {

    .x-button {
      width: 100%;
      margin-top: 8px;
    }
  }
</style>