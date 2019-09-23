<template>
  <x-modal
    class="x-user-config"
    @close="onClose"
    @confirm="performUserConfig"
  >
    <div slot="body">
      <x-form
        v-model="userToConfig"
        :schema="userSchema"
        @validate="validateUser"
      />
    </div>
    <template slot="footer">
      <x-button
        link
        @click="onClose"
      >Cancel
      </x-button>
      <x-button
        :disabled="!validUser"
        @click="performUserConfig"
      >{{ editMode ? 'Update User' : 'Create User' }}
      </x-button>
    </template>
  </x-modal>
</template>

<script>
  import xForm from '../../neurons/schema/Form.vue'
  import xModal from '../../axons/popover/Modal.vue'
  import xButton from '../../axons/inputs/Button.vue'

  import { mapState, mapActions, mapMutations } from 'vuex'
  import {
    CREATE_USER, UPDATE_USER, GET_ALL_ROLES
  } from '../../../store/modules/auth'
  import {SHOW_TOASTER_MESSAGE} from '../../../store/mutations'

  export default {
    name: 'XUserConfig',
    components: { xForm, xModal, xButton },
    props: {
      user: {
        type: Object,
        default: null
      }
    },
    data () {
      return {
        userToConfig: null,
        validUser: true
      }
    },
    computed: {
      ...mapState({
        roles (state) {
          return state.auth.allRoles.data
        }
      }),
      editMode() {
        return this.user && this.user.uuid
      },
      userSchema () {
        return {
          type: 'array', items: [{
            name: 'user_name',
            title: 'Username',
            type: 'string',
            readOnly: this.editMode
          }, {
            name: 'password',
            title: 'Password',
            type: 'string',
            format: 'password'
          }, {
            name: 'first_name',
            title: 'First name',
            type: 'string'
          }, {
            name: 'last_name',
            title: 'Last name',
            type: 'string'
          }, {
            name: 'role_name',
            title: 'Role',
            type: 'string',
            enum: !this.editMode ? this.roles.map(item => item.name) : null,
            readOnly: this.editMode,
            placeholder: 'CUSTOM'
          }],
          required: ['user_name', 'password']
        }
      },
      newUserTemplate () {
        return this.userSchema.items.reduce((map, item) => {
          map[item.name] = ''
          return map
        }, {})
      }
    },
    created () {
      if(!this.editMode){
        this.userToConfig = {...this.newUserTemplate}
      } else {
        this.userToConfig = this.user
      }
      this.getAllRoles()
    },
    methods: {
      ...mapActions({
        createUser: CREATE_USER, updateUser: UPDATE_USER,
        getAllRoles: GET_ALL_ROLES
      }),
      ...mapMutations({
        showToasterMessage: SHOW_TOASTER_MESSAGE
      }),
      validateUser(valid) {
        this.validUser = valid
      },
      performUserConfig () {
        if(this.editMode){
          let userToUpdate = {}
          let updateFields = ['first_name', 'last_name', 'password']
          updateFields.forEach(field =>{
              userToUpdate[field] = this.userToConfig[field]
          })
          this.updateUser({uuid: this.userToConfig.uuid, user: userToUpdate}).then(response => {
            this.showToasterMessage({ message: response && response.status === 200 ? 'User updated.' : response.data.message })
            this.onClose()
          }).catch(error => this.$emit('toast', error.response.data.message))
        } else {
          this.createUser(this.userToConfig).then(response => {
            this.showToasterMessage({ message: response && response.status === 200 ? 'User created.' : response.data.message })
            this.onClose()
          }).catch(error => this.$emit('toast', error.response.data.message))
        }
      },
      onClose(){
        this.$emit('exit', true)
      }
    }
  }
</script>

<style lang="scss">
  .x-user-config {

    .x-form {
      text-align: left;

      .x-array-edit {
        grid-template-columns: 1fr 1fr 1fr;
      }

      .error {
        display: none;
      }
    }
  }
</style>