import {
  mapActions,
  mapMutations,
  mapGetters,
  mapState,
} from 'vuex';
import _get from 'lodash/get';
import _set from 'lodash/set';
import _cloneDeep from 'lodash/cloneDeep';
import { required } from 'vuelidate/lib/validators';

import XButton from '@axons/inputs/Button.vue';
import XSidePanel from '@networks/side-panel/SidePanel.vue';
import { xActionItem, xActionsGroup } from '@networks/side-panel/PanelActions';
import XCheckbox from '@axons/inputs/Checkbox.vue';
import XCombobox from '@axons/inputs/combobox/index.vue';

import { mdiContentDuplicate, mdiDelete, mdiPencil } from '@mdi/js';

import './role-panel.scss';
import {
  CHANGE_ROLE,
  CREATE_ROLE,
  REMOVE_ROLE,
  GET_PERMISSION_STRUCTURE,
} from '@store/modules/auth';
import { GET_LABELS } from '@store/modules/labels';
import { getPermissionState, PermissionCategoryState } from '@constants/permissions';
import { getRoleUserCount, fetchAssignableRolesList } from '@api/roles';
import { SHOW_TOASTER_MESSAGE } from '@store/mutations';

export const FormMode = {
  ViewRole: 'ViewRole',
  CreateRole: 'CreateRole',
  EditRole: 'EditRole',
  DuplicateRole: 'DuplicateRole',
};

function uniqueRoleName(value) {
  if (this.role.uuid && this.role.name === value) {
    return true;
  }
  let included = false;
  for (let i = 0; i < this.roleNamesList.length; i++) {
    const currentName = this.roleNamesList[i];
    if (value && currentName.text.toLocaleLowerCase() === value.toLocaleLowerCase()) {
      included = true;
      break;
    }
  }
  return !included;
}

export default {
  name: 'xRolePanel',
  components: {
    XButton,
    XSidePanel,
    xActionItem,
    xActionsGroup,
    XCheckbox,
    XCombobox,
  },
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    role: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      name: '',
      permissions: {},
      expandedCategories: [],
      mode: FormMode.ViewRole,
      inSaveMode: false,
      roleNamesList: [],
    };
  },
  validations: {
    name: { required, uniqueRoleName },
  },
  computed: {
    ...mapState({
      roles(state) {
        return state.auth.allRoles.data;
      },
    }),
    ...mapGetters({
      getLabels: GET_LABELS,
      getPermissionsStructure: GET_PERMISSION_STRUCTURE,
    }),
    currentRole() {
      const role = { name: this.name, permissions: this.permissions };
      if (this.role.uuid) {
        role.uuid = this.role.uuid;
      }
      return role;
    },
    roleNameErrorMsg() {
      const { name } = this.$v;
      let errMsg = '';
      if (!name.required) {
        errMsg = 'Name is a required field';
      } else if (!name.uniqueRoleName) {
        errMsg = 'Name already exists. Please enter a different Name.';
      }
      return errMsg;
    },
    isFormInvalid() {
      return this.$v.$invalid;
    },
    roleId() {
      return this.role.uuid;
    },
    isPredefined() {
      return this.role.predefined;
    },
    userCanAddRole() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Add, this.$permissionConsts.categories.Roles);
    },
    userCanEditRoles() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update, this.$permissionConsts.categories.Roles);
    },
    userCanDeleteRoles() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Delete, this.$permissionConsts.categories.Roles);
    },
    permissionStructureMap() {
      const map = {};
      this.getPermissionsStructure.forEach((permissionCategory) => {
        const categoryName = permissionCategory.name;
        map[categoryName] = permissionCategory.actions.map((permissionActionKey) => permissionActionKey.replace('permissions.', ''));
      });
      return map;
    },
    getCategoriesStates() {
      return this.getPermissionsStructure.map((permissionCategory) => {
        const categoryName = permissionCategory.name;
        return getPermissionState(this.getLabels, categoryName, this.currentRole);
      });
    },
  },
  watch: {
    role(newRole) {
      this.$v.$reset();
      this.name = newRole.name;
      this.permissions = _cloneDeep(newRole.permissions);
      this.expandedCategories = [];
      this.mode = newRole.uuid ? FormMode.ViewRole : FormMode.CreateRole;
      this.inSaveMode = false;
    },
  },
  async created() {
    this.updateAssignableRolesList();
  },
  methods: {
    ...mapActions({
      createRole: CREATE_ROLE,
      changeRole: CHANGE_ROLE,
      removeRole: REMOVE_ROLE,
    }),
    ...mapMutations({
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    validate() {
      this.$v.$touch();
    },
    onChangeCategoryCheckbox(event, categoryName, prevState) {
      const nextState = prevState !== PermissionCategoryState.full;
      this.updatePermissionCategory(categoryName, nextState);
      event.stopPropagation();
    },
    renderPermissionCategory(permissionCategory, index) {
      if (!this.permissions || !this.getLabels) {
        return null;
      }
      const categoryLabelKey = permissionCategory.category;
      const categoryActions = permissionCategory.actions;
      const categoryName = permissionCategory.name;
      const userCategoryPermissions = this.permissions[categoryName];
      const categoryState = this.getCategoriesStates[index];
      return (
          <v-expansion-panel class={categoryName}>
            <v-expansion-panel-header
            >
              <v-checkbox
              input-value={categoryState === PermissionCategoryState.full}
              indeterminate={categoryState === PermissionCategoryState.partial}
              label={this.getLabels[categoryLabelKey]}
              disabled={this.isPredefined || this.mode === FormMode.ViewRole}
              color="#1D222C"
              onClick={(event) => {
                this.onChangeCategoryCheckbox(event, categoryName, categoryState);
              }}
              />
          </v-expansion-panel-header>
            {
              categoryActions.map((valueLabelKey) => {
                const permissionKey = valueLabelKey.replace(`permissions.${categoryName}.`, '');
                const currentPermission = _get(userCategoryPermissions, permissionKey, false);
                if (currentPermission !== undefined) {
                  return (
                    <v-expansion-panel-content>
                      <XCheckbox
                        data={currentPermission}
                        value={permissionKey}
                        label={this.getLabels[valueLabelKey]}
                        read-only={this.isPredefined || this.mode === FormMode.ViewRole}
                        onChange={
                          (value) => this.updatePermissionValue(categoryName, permissionKey, value)
                        }
                      />
                    </v-expansion-panel-content>
                  );
                }
                return null;
              })
            }
        </v-expansion-panel>
      );
    },
    updatePermissionCategory(categoryName, value) {
      this.permissionStructureMap[categoryName].forEach((permissionStructureKey) => {
        _set(this.permissions, permissionStructureKey, value);
      });
    },
    updatePermissionValue(category, key, value) {
      _set(this.permissions, `${category}.${key}`, value);
    },
    async saveRole() {
      this.validate();
      if (!this.isFormInvalid) {
        try {
          if (this.role.uuid) {
            const userCount = await getRoleUserCount(this.role.uuid);
            if (userCount) {
              this.inSaveMode = true;
              this.$safeguard.show({
                text: `
                    <b>Role Permission changes</b><br>
                    This will affect ${userCount} user associated with this role.\n
                    Are you sure you want to continue?
                    `,
                confirmText: 'Yes',
                onConfirm: async () => {
                  await this.updateRole();
                  this.inSaveMode = false;
                },
                onCancel: () => {
                  this.inSaveMode = false;
                },
              });
            } else {
              this.updateRole();
            }
          } else {
            await this.createRole(this.currentRole);
            this.showToasterMessage({ message: 'Role created.' });
            this.updateAssignableRolesList();
            this.closePanel();
          }
        } catch (e) {
          if (e.response.status < 500) {
            this.showToasterMessage({ message: e.response.data.message });
            this.inSaveMode = false;
          }
        }
      }
    },
    async updateRole() {
      try {
        await this.changeRole(this.currentRole);
        this.showToasterMessage({ message: 'Role saved.' });
        this.updateAssignableRolesList();
        this.closePanel();
      } catch (e) {
        this.showToasterMessage({ message: 'Failed to save role.' });
      }
    },
    async updateAssignableRolesList() {
      this.roleNamesList = await fetchAssignableRolesList();
    },
    async deleteRole() {
      try {
        this.inSaveMode = true;
        await this.removeRole(this.role);
        this.inSaveMode = false;
        this.showToasterMessage({ message: 'Role deleted.' });
        this.updateAssignableRolesList();
        this.closePanel();
      } catch (e) {
        if (e.response && e.response.status < 500) {
          this.$messageModal.show({
            text: `
                  <b>Role can't be deleted</b><br>
                  ${e.response.data.message}
                  `,
            confirmText: 'Okay',
            hideCancel: true,
            onConfirm: async () => {
              this.inSaveMode = false;
            },
          });
        }
      }
    },
    closePanel() {
      this.$emit('input', false);
    },
    duplicateRole() {
      this.mode = FormMode.DuplicateRole;
      this.$emit('duplicate');
    },
    setNameField(e) {
      this.name = e.target.value;
      this.$v.name.$touch();
    },
    toggleEditNameMode() {
      this.mode = FormMode.EditRole;
    },
    genNameMarkup() {
      const nameError = this.$v.name.$error;
      const nameRequired = !this.$v.name.required;
      // return name field markup if in create edit or duplicate mode. Else, return null.
      return ((this.role.uuid && this.userCanEditRoles) || this.userCanAddRole)
      && this.mode !== FormMode.ViewRole ? (
          <div class="item form__name">
            <h5>Name</h5>
            <input
              value={this.name}
              onInput={this.setNameField}
              class="name_input"
              maxLength={30}
            />
            {nameError && <p class="error-input indicator-error--text">{nameRequired ? 'Name is a required field' : 'Name is used by another role'}</p>}
          </div>
        ) : null;
    },
    genActionsButtonsMarkup() {
      const actions = [];
      if (this.userCanEditRoles && !this.isPredefined && this.mode === FormMode.ViewRole) {
        actions.push(<x-action-item
          class="action-edit"
          title="Edit"
          onClick={this.toggleEditNameMode}
          size="20"
          color="#fff"
          icon={mdiPencil}
        />);
      }

      if (this.roleId && this.userCanAddRole && this.mode === FormMode.ViewRole) {
        actions.push(<x-action-item
          class="action-duplicate"
          title="Duplicate"
          onClick={this.duplicateRole}
          size="20"
          color="#fff"
          icon={mdiContentDuplicate}
        />);
      }
      if (this.roleId && this.userCanDeleteRoles
        && !this.isPredefined && this.mode === FormMode.ViewRole) {
        actions.push(<x-action-item
          class="action-remove"
          title="Remove"
          onClick={this.deleteRole}
          size="20"
          color="#fff"
          icon={mdiDelete}
        />);
      }
      return actions;
    },
    expandAll() {
      this.expandedCategories = Array.from(Array(this.getPermissionsStructure.length).keys());
    },
    collapseAll() {
      this.expandedCategories = [];
    },
  },
  render(h) {
    return (
        <XSidePanel
            value={this.value}
            panelClass="role-panel"
            title={this.name}
            onInput={(value) => this.$emit('input', value)}
            temporary={!this.inSaveMode && this.value}
        >
            {
                <x-actions-group slot="panelHeader">
                    {this.genActionsButtonsMarkup()}
                </x-actions-group>

            }
            <div slot="panelContent" class="body">
              {this.genNameMarkup()}
              <div class="collapse-expand-buttons">
                <XButton
                  link
                  onClick={this.expandAll}
                >Expand All</XButton>
                <XButton
                  link
                  onClick={this.collapseAll}
                >Collapse All</XButton>
              </div>
              <v-expansion-panels
                value={this.expandedCategories}
                multiple
                accordion
              >
                { this.getPermissionsStructure.map(
                  (permissionCategory, index) => this.renderPermissionCategory(permissionCategory,
                    index),
                )}
              </v-expansion-panels>
            </div>
            <div slot="panelFooter">
              <div class="left-buttons">
                <XButton
                link
                onClick={this.closePanel}>Cancel</XButton>
              </div>
                <div class="buttons">
                  {
                    (!this.isPredefined && this.mode !== FormMode.ViewRole
                      && ((this.userCanEditRoles && this.roleId)
                        || (this.userCanAddRole && !this.roleId)))
                      ? (<XButton
                        onClick={this.saveRole}
                        disabled={this.isFormInvalid}
                        >Save</XButton>) : null
                  }
                </div>
            </div>
        </XSidePanel>
    );
  },
};
