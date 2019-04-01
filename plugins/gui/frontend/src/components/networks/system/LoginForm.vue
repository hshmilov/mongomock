<template>
  <div class="x-login-form">
    <h3 class="title">Login</h3>
    <x-form
      v-model="credentials"
      :schema="schema"
      :error="prettyUserError"
      @input="initError"
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
        this.login(this.credentials)
      }
    }
  }
</script>

<style lang="scss">

</style>