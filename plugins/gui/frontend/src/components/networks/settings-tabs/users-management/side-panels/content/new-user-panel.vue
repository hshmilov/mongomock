<template>
  <div class="new-user__form">

    <!-- user name -->
    <div class="item form__name">
      <h5>User Name</h5>
      <input
        v-model="$v.userName.$model"
        placeholder="Enter User Name"
        class="username__input"
      >
      <p
        v-if="$v.userName.$error"
        class="error-input indicator-error--text"
      >
        {{ userNameErrorMsg }}
      </p>
    </div>

    <!-- first name -->
    <div class="item form__first-name">
      <h5>First Name</h5> (optional)
      <input
        v-model="firstName"
        placeholder="Enter First Name"
        class="first-name__input"
      >
    </div>

    <!-- last name -->
    <div class="item form__last-name">
      <h5>Last Name</h5> (optional)
      <input
        v-model="lastName"
        placeholder="Enter Last Name"
        class="last-name__input"
      >
    </div>

    <!-- email -->
    <div class="item form__email">
      <h5>Email</h5> (optional)
      <input
        v-model="$v.email.$model"
        placeholder="Enter Email"
        class="email__input"
      >
      <p
        v-if="$v.email.$error"
        class="error-input indicator-error--text"
      >Please enter a valid email address to use for your Axonius system</p>
    </div>

    <!-- role -->
    <div class="item form__role">
      <h5>Role</h5>
      <ASelect
        v-model="$v.role.$model"
        placeholder="Select Role"
      >
        <ASelectOption
          v-for="selectRole in rolesOptions"
          :key="selectRole.value"
        >
          {{ selectRole.text }}
        </ASelectOption>
      </ASelect>
      <p
        v-if="$v.role.$error"
        class="error-input indicator-error--text"
      >Please select a permissions role for this user</p>
    </div>
    <!-- password -->
    <div class="item form__password">
      <h5>Password</h5>
      <input
        v-model="$v.password.$model"
        placeholder="Enter Password"
        class="password__input"
      >
      <p
        v-if="$v.password.$error"
        class="error-input indicator-error--text"
      >Please select a password for this user</p>
    </div>

  </div>
</template>

<script>
import { Select } from 'ant-design-vue';
import { mapState, mapActions } from 'vuex';
import { required, email } from 'vuelidate/lib/validators';
import { fetchAssignableRolesList } from '@api/roles';
import { fetchUsernamesList } from '@api/system-users';
import {
  GET_ALL_ROLES,
} from '@store/modules/auth';

function uniqueUsername(value) {
  let included = false;
  for (let i = 0; i < this.usernamesList.length; i++) {
    const currentName = this.usernamesList[i];
    if (currentName.toLocaleLowerCase() === value.toLocaleLowerCase()) {
      included = true;
      break;
    }
  }
  return !included;
}

export default {
  name: 'XNewUserPanelContent',
  components: {
    ASelect: Select,
    ASelectOption: Select.Option,
  },
  props: {
    valid: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      userName: '',
      firstName: '',
      lastName: '',
      email: '',
      role: undefined,
      password: '',
      usernamesList: [],
      rolesOptions: [],
    };
  },
  validations: {
    userName: { required, uniqueUsername },
    email: { email },
    role: { required },
    password: { required },
  },
  computed: {
    userNameErrorMsg() {
      const { userName } = this.$v;
      let errMsg = '';
      if (!userName.required) {
        errMsg = 'User Name is a required field';
      } else if (!userName.uniqueUsername) {
        errMsg = 'User Name already exists. Please enter a different User Name.';
      }
      return errMsg;
    },
    isFormInvalid() {
      return this.$v.$invalid;
    },
    userInfo() {
      return {
        user_name: this.userName,
        first_name: this.firstName,
        last_name: this.lastName,
        email: this.email,
        password: this.password,
        role_id: this.role,
      };
    },
  },
  watch: {
    isFormInvalid(value) {
      this.$emit('validate', value);
    },
    userInfo(user) {
      this.$emit('change', user);
    },
  },
  async created() {
    this.fetchSystemRoles();
    this.usernamesList = await fetchUsernamesList();
    this.rolesOptions = await fetchAssignableRolesList();
  },
  methods: {
    ...mapActions({
      fetchSystemRoles: GET_ALL_ROLES,
    }),
    validate() {
      this.$v.$touch();
      return this.$v.$invalid;
    },
  },
};
</script>

<style lang="scss">
.user-panel {
  .new-user__form {
    width: 390px;
    h5 {
      display: inline;
      font-size: 16px;
      font-weight: 400;
      color: $theme-black;
      margin: 0 0 3px 0;
    }
    input {
      display: block;
      width: 100%;
      height: 30px;
      padding: 4px;
    }
    .ant-select {
      display: block;
      width: 100%;
      height: 30px;
      padding-bottom: 4px;
    }
    .item {
      margin: 0 0 16px 0;
    }

    .v-select.v-text-field input {
      border-style: none;
      visibility: hidden;
    }
    .v-text-field__details {
      display: none !important;
    }
  }
  .x-side-panel__footer {
    > div {
      display: flex;
      flex-direction: column;
      .indicator-error--text {
        display: flex;
        justify-content: flex-end;
      }
      .buttons {
        display: flex;
        flex: 50%;
        justify-content: flex-end;
      }
    }
  }
}
</style>
