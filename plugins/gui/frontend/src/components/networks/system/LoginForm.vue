<template>
  <div class="x-login-form">
    <h3 class="login-title">
      Login
    </h3>
    <XForm
      v-model="credentials"
      :schema="schema"
      :error="prettyUserError"
      @validate="onValidate"
      @submit="onLogin"
    />
    <XButton
      type="primary"
      :disabled="invalidForm"
      @click="onLogin"
    >Login</XButton>
  </div>
</template>

<script>
import { mapActions } from 'vuex';
import XForm from '../../neurons/schema/Form.vue';
import XButton from '../../axons/inputs/Button.vue';
import userErrorMixin from '../../../mixins/user_error';
import { GettingStartedPubSub } from '../../App.vue';

import { LOGIN } from '../../../store/modules/auth';
import { Modal } from 'ant-design-vue'

export default {
  name: 'XLoginForm',
  components: {
    XForm, XButton,
  },
  mixins: [userErrorMixin],
  props: {
    settings: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      credentials: {
        user_name: '',
        password: '',
        remember_me: false,
      },
      invalidForm: true,
      items: [
        { name: 'user_name', title: 'User Name', type: 'string' },
        {
          name: 'password', title: 'Password', type: 'string', format: 'password',
        },
        {
          name: 'remember_me', title: 'Remember me', type: 'bool', default: false,
        },
      ],
      requiredItems: ['user_name', 'password', 'remember_me'],
    };
  },
  computed: {
    schema() {
      return {
        type: 'array',
        required: this.settings.standard.disable_remember_me ? this.requiredItems.filter((field) => field !== 'remember_me') : this.requiredItems,
        items: this.settings.standard.disable_remember_me ? this.items.filter((item) => item.name !== 'remember_me') : this.items,
      };
    },
  },
  methods: {
    ...mapActions({ login: LOGIN }),
    onValidate(valid) {
      this.invalidForm = !valid;
    },
    onLogin() {
      this.login(this.credentials).then((res) => {
        if (res.status === 200) {
          // Set getting started panel state to open=true
          GettingStartedPubSub.$emit('getting-started-login');
        }
      }).catch((error) => {
        const errorMessage = error.response.data.message;
        if (errorMessage && errorMessage === 'password expired') {
          const token = error.response.data.additional_data.split('token=')[1];
          Modal.confirm({
            title: 'Password Expired',
            content: 'Your password has expired and must be changed',
            cancelButtonProps: { style: { display: 'none' } },
            icon: 'exclamation-circle',
            centered: true,
            onOk: () => this.$router.push({ path: '/', query: { token } }),
          });
        }
      });
    },
  },
};
</script>

<style lang="scss">
  .x-login-form {

    .x-button {
      width: 100%;
      margin-top: 8px;
    }
  }
</style>
