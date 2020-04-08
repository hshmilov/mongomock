<script>

import { mapGetters, mapActions, mapMutations } from 'vuex';
import { mdiDelete } from '@mdi/js';

import {
  GET_SYSTEM_USERS_MAP,
  CREATE_USER,
  UPDATE_USER,
  GET_ADMIN_USER_ID,
} from '@store/modules/auth';
import XSidePanel from '@networks/side-panel/SidePanel.vue';
import {
  xActionItem as XActionItem,
  xActionsGroup as XActionsGroup,
} from '@networks/side-panel/PanelActions';
import XButton from '@axons/inputs/Button.vue';
import { SHOW_TOASTER_MESSAGE } from '@store/mutations';

const XNewUserForm = () => import(/* webpackChunkName: "XNewUserForm" */ './content/new-user-panel.vue');
const XEditUserInfoForm = () => import(/* webpackChunkName: "XEditUserInfoForm" */ './content/edit-user-panel.vue');

export default {
  name: 'UserPanel',
  components: {
    XButton,
    XSidePanel,
    XActionItem,
    XActionsGroup,
    XNewUserForm,
    XEditUserInfoForm,
  },
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    panelType: {
      type: String,
      validator: function panelTypePropValidator(value) {
        // The value must match one of these options
        return ['new', 'internal', 'external'].indexOf(value) !== -1;
      },
      default: 'new',
    },
    userId: {
      type: String,
      default: undefined,
    },
    title: {
      type: String,
      default: 'New User',
    },
  },
  data() {
    return {
      isFormInvalid: false,
      userInfo: null,
    };
  },
  computed: {
    ...mapGetters({
      usersMap: GET_SYSTEM_USERS_MAP,
      systemAdminUuid: GET_ADMIN_USER_ID,
    }),
    canDeleteUser() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Delete,
        this.$permissionConsts.categories.Users);
    },
  },
  watch: {
    userId(id) {
      this.userInfo = this.usersMap[id];
    },
  },
  methods: {
    ...mapMutations({
      showSnackbar: SHOW_TOASTER_MESSAGE,
    }),
    ...mapActions({
      createNewUser: CREATE_USER,
      updateUser: UPDATE_USER,
    }),
    onPanelStateChange(isOpen) {
      if (!isOpen) {
        this.onCancel();
      }
      this.$emit('input', isOpen);
    },
    genPanelActions() {
      if (this.panelType !== 'new') {
        return this.canDeleteUser && this.systemAdminUuid !== this.userId ? (
          <x-action-item
            class="action-remove"
            title="Remove"
            onClick={this.callDeleteUser}
            size="20"
            color="#fff"
            icon={mdiDelete}
          />
        ) : null;
      }
      return null;
    },
    genPanelContent() {
      if (this.panelType === 'new') {
        return <XNewUserForm ref="form" onValidate={this.validate} onChange={this.syncUserInfo}/>;
      }
      return this.userInfo
        ? <XEditUserInfoForm
            ref="form"
            userType={this.panelType}
            user={this.userInfo}
            onValidate={this.validate}
            onChange={this.syncUserInfo}/>
        : null;
    },
    syncUserInfo(userInfo) {
      this.userInfo = {
        ...this.userInfo,
        ...userInfo,
      };
    },
    validate(value) {
      this.isFormInvalid = value;
    },
    async onSave() {
      const invalid = this.$refs.form.validate();

      this.validate(invalid);
      if (!invalid) {
        let res;
        const errorMessage = 'Oppsssss somthing went wrong!';

        try {
          let snackbarMessage = '';
          if (this.panelType === 'new') {
            snackbarMessage = 'User created successfully';
            res = await this.createNewUser(this.userInfo);
          } else {
            snackbarMessage = 'User updated successfully';
            res = await this.updateUser({
              uuid: this.userId,
              user: this.userInfo,
            });
          }
          this.showSnackbar({ message: res.status === 200 ? snackbarMessage : errorMessage });
          if (res.status === 200) {
            this.onCancel();
          }
        } catch (ex) {
          if (ex.response.status < 500) {
            this.showSnackbar({ message: ex.response.data.message });
          } else {
            this.showSnackbar({ message: errorMessage });
          }
        }
      }
    },
    callDeleteUser() {
      this.$emit('delete');
    },
    onCancel() {
      this.isFormInvalid = false;
      this.$emit('close');
    },
  },
  // eslint-disable-next-line no-unused-vars
  render(h) {
    return (
      <XSidePanel
        value={this.value}
        title={this.title}
        panel-class="user-panel"
        onInput={this.onPanelStateChange}
      >
        <XActionsGroup slot="panelHeader">
          {this.genPanelActions()}
        </XActionsGroup>
        <div
          slot="panelContent"
          class="body"
        >
          {
            this.value ? this.genPanelContent() : null
          }
        </div>
        <div slot="panelFooter">
          <div class="buttons">
            <XButton onClick={this.onSave} disabled={this.isFormInvalid}>Save</XButton>
            <XButton onClick={this.onCancel} link>Cancel</XButton>
          </div>
        </div>
      </XSidePanel>
    );
  },
};

</script>
