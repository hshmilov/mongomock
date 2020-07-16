<template>
  <div class="edit-user">
    <div class="edit-user__form">
      <!-- first name -->
      <div class="item form__first-name">
        <h5>First Name</h5> (optional)
        <input
          v-model="firstName"
          type="text"
          placeholder="Enter First Name"
          class="first-name__input"
          :disabled="isExternalUser || isSystemAdminPanel"
        >
      </div>

      <!-- last name -->
      <div class="item form__last-name">
        <h5>Last Name</h5> (optional)
        <input
          v-model="lastName"
          type="text"
          placeholder="Enter Last Name"
          class="last-name__input"
          :disabled="isExternalUser || isSystemAdminPanel"
        >
      </div>

      <!-- email -->
      <div class="item form__email">
        <h5>Email</h5> (optional)
        <input
          v-model="$v.email.$model"
          type="text"
          placeholder="Enter Email"
          class="email__input"
          :disabled="isExternalUser"
        >
        <p
          v-if="$v.email.$error"
          class="error-input indicator-error--text"
        >
          Please enter a valid email address to use for your Axonius system
        </p>
      </div>

      <!-- role -->
      <div class="item form__role">
        <h5>Role</h5>
        <ASelect
          v-model="$v.role.$model"
          placeholder="Select Role"
          :disabled="isSystemAdminPanel"
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
        >
          Please enter a valid email address to use for your Axonius system
        </p>
      </div>
      <!-- password -->
      <div
        v-if="isInternalUser"
        class="item form__password"
      >
        <h5>Password</h5>
        <input
          v-model="$v.password.$model"
          placeholder="Enter Password"
          class="password__input"
          type="password"
          @focusin="onFocusIn"
        >
        <p
          v-if="$v.password.$error"
          class="error-input indicator-error--text"
        >Please select a password for this user</p>
      </div>
      <div
        v-else
        class="item form__source"
      >
        <h5 class="grey3--text">Ignore role assignment rules</h5>
        <input
          v-model="user.ignore_role_assignment_rules"
          type="checkbox"
        >
        <h5 class="grey3--text">Source</h5>
        <p class="source--text">{{ user.source }}</p>
      </div>
    </div>
    <div class="edit-user__avatar">
      <VAvatar size="120">
        <img
          :src="user.pic_name"
          alt="avatar"
        >
      </VAvatar>
    </div>
  </div>
</template>

<script>
import { Select } from 'ant-design-vue';
import { mapActions, mapGetters } from 'vuex';
import { required, email } from 'vuelidate/lib/validators';
import { GET_ALL_ROLES, GET_ADMIN_USER_ID } from '@store/modules/auth';
import { fetchAssignableRolesList } from '@api/roles';

export default {
  name: 'XEditUserForm',
  components: {
    ASelect: Select,
    ASelectOption: Select.Option,
  },
  props: {
    valid: {
      type: Boolean,
      default: false,
    },
    userType: {
      type: String,
      validator: function panelTypePropValidator(value) {
        // The value must match one of these options
        return ['internal', 'external'].indexOf(value) !== -1;
      },
      default: 'internal',
    },
    user: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      uuid: this.user.uuid,
      firstName: this.user.first_name,
      lastName: this.user.last_name,
      email: this.user.email,
      role: this.user.role_id,
      password: this.user.password,
      ignore_role_assignment_rules: this.user.ignore_role_assignment_rules,
      rolesOptions: [],
    };
  },
  validations: {
    email: { email },
    role: { required },
    password: { required },
  },
  computed: {
    ...mapGetters({
      systemAdminUuid: GET_ADMIN_USER_ID,
    }),
    isFormInvalid() {
      return this.$v.$invalid;
    },
    isInternalUser() {
      return this.userType === 'internal';
    },
    isExternalUser() {
      return this.userType === 'external';
    },
    userInfo() {
      const userInfo = {
        first_name: this.firstName,
        last_name: this.lastName,
        email: this.email,
        role_id: this.role,
      };

      if (this.isInternalUser) {
        userInfo.password = this.password;
      } else {
        userInfo.ignore_role_assignment_rules = this.ignore_role_assignment_rules;
      }
      return userInfo;
    },
    isSystemAdminPanel() {
      return this.systemAdminUuid === this.uuid;
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
    onFocusIn(event) {
      if (this.$v.password.$model[0] === 'unchanged') {
        event.target.select();
      }
    },
  },
};
</script>

<style lang="scss">
.user-panel {
  .edit-user {
    display: flex;
    flex-direction: row;
    justify-content: space-between;

    .edit-user__form {
      width: 390px;

      h5 {
        display: inline;
        font-size: 16px;
        font-weight: 400;
        color: $theme-black;
        margin: 0 0 3px 0;
      }

      input{
        display: block;
        height: 30px;
        padding: 4px;
      }
      input[type="text"] {
        width: 100%;
      }
      input[type="checkbox"] {
        width: 16px;
        margin-bottom: 12px;
      }
      .source--text {
        text-transform: uppercase;
      }

      .ant-select {
        display: block;
        width: 100%;
        height: 30px;
        padding-bottom: 4px;

        &.ant-select-disabled {
          .ant-select-selection {
            background-color: $grey-2;
            border-color: $grey-3;
            border-width: 1px;
            border-style: solid;
            opacity: 0.6;
          }
        }

      }

      .item {
        margin: 0 0 16px 0;
      }

      .v-select.v-text-field input {
        border-style: none;
        visibility: hidden;
      }
    }

    .v-text-field__details {
      display: none !important;
    }
  }
  .ant-drawer-body__footer {
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
