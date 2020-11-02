import {
  mapActions, mapGetters, mapMutations, mapState,
} from 'vuex';
import _get from 'lodash/get';
import _set from 'lodash/set';
import _cloneDeep from 'lodash/cloneDeep';
import { required } from 'vuelidate/lib/validators';

import XSidePanel from '@networks/side-panel/SidePanel.vue';
import { xActionItem, xActionsGroup } from '@networks/side-panel/PanelActions';
import XCheckbox from '@axons/inputs/Checkbox.vue';
import XCombobox from '@axons/inputs/combobox/index.vue';

import './role-panel.scss';
import {
  CHANGE_ROLE,
  CREATE_ROLE,
  GET_PERMISSION_STRUCTURE,
  REMOVE_ROLE,
} from '@store/modules/auth';
import { GET_LABELS } from '@store/modules/labels';
import { getPermissionState, PermissionCategoryState } from '@constants/permissions';
import { fetchAssignableRolesList, getRoleUserCount } from '@api/roles';
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
    XSidePanel,
    xActionItem,
    xActionsGroup,
    XCheckbox,
    XCombobox,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    role: {
      type: Object,
      default: () => {
      },
    },
    title: {
      type: String,
      default: 'New Role',
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
    name: {
      required,
      uniqueRoleName,
    },
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
      const role = {
        name: this.name,
        permissions: this.permissions,
      };
      if (this.role.uuid) {
        role.uuid = this.role.uuid;
      }
      return role;
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
      this.resetRole(newRole);
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
    resetRole(fromRole) {
      this.name = fromRole.name;
      this.permissions = _cloneDeep(fromRole.permissions);
      this.expandedCategories = [];
    },
    validate() {
      this.$v.$touch();
    },
    onChangeCategoryCheckbox(event, categoryName, prevState) {
      const nextState = prevState !== PermissionCategoryState.full;
      this.updatePermissionCategory(categoryName, nextState);
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
          <v-expansion-panel-header>
            <div>
              <XCheckbox
                data={categoryState === PermissionCategoryState.full}
                value={categoryName}
                indeterminate={categoryState === PermissionCategoryState.partial}
                label={this.getLabels[categoryLabelKey]}
                read-only={this.isPredefined || this.mode === FormMode.ViewRole}
                onChange={(event) => {
                  this.onChangeCategoryCheckbox(event, categoryName, categoryState);
                }}
              />
            </div>
          </v-expansion-panel-header>
          {
            categoryActions.map((valueLabelKey) => {
              const permissionKey = valueLabelKey.replace(`permissions.${categoryName}.`, '');
              const currentPermission = _get(userCategoryPermissions, permissionKey, false);
              if (currentPermission !== undefined) {
                return (
                  <v-expansion-panel-content eager={true}>
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
            this.showToasterMessage({ message: 'Role created' });
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
        this.showToasterMessage({ message: 'Role saved' });
        this.updateAssignableRolesList();
        this.closePanel();
      } catch (e) {
        this.showToasterMessage({ message: 'Failed to save role' });
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
        this.showToasterMessage({ message: 'Role deleted' });
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
      this.$emit('close', false);
    },
    duplicateRole() {
      this.mode = FormMode.DuplicateRole;
      this.$emit('duplicate');
    },
    setNameField(e) {
      this.name = e.target.value;
      this.$v.name.$touch();
    },
    toggleEditMode() {
      this.mode = this.mode === FormMode.ViewRole ? FormMode.EditRole : FormMode.ViewRole;
      if (this.mode === FormMode.ViewRole) {
        this.resetRole(this.role);
      }
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
            type="text"
            onInput={this.setNameField}
            placeholder="New Role"
            class="name_input"
            maxLength={30}
          />
          {nameError && <p
            class="error-input indicator-error--text">{nameRequired ? 'Name is a required field' : 'Name is used by another role'}</p>}
        </div>
        ) : null;
    },
    genActionsButtonsMarkup() {
      const actions = [];
      if (this.userCanEditRoles && !this.isPredefined && this.mode === FormMode.ViewRole) {
        actions.push(<x-action-item
          class="action-edit"
          title="Edit"
          onClick={this.toggleEditMode}
          type="edit"
        />);
      }

      if (this.roleId && this.userCanAddRole && this.mode === FormMode.ViewRole) {
        actions.push(<x-action-item
          class="action-duplicate"
          title="Duplicate"
          onClick={this.duplicateRole}
          type="copy"
        />);
      }
      if (this.roleId && this.userCanDeleteRoles
        && !this.isPredefined && this.mode === FormMode.ViewRole) {
        actions.push(<x-action-item
          class="action-remove"
          title="Delete"
          onClick={this.deleteRole}
          type="delete"
        />);
      }
      return actions;
    },
    expandAll() {
      this.expandedCategories = Array.from(Array(this.getPermissionsStructure.length)
        .keys());
    },
    collapseAll() {
      this.expandedCategories = [];
    },
    getSidePanelContainer() {
      return document.querySelector('.x-tabs .body');
    },
  },
  render() {
    return (
       <XSidePanel
          visible={this.visible}
          panel-container={this.getSidePanelContainer}
          panelClass={`role-panel ${this.mode !== FormMode.ViewRole ? 'with-footer' : ''}`}
          title={this.title}
          onClose={this.closePanel}
        >
          {
            <x-actions-group slot="panelHeader">
              {this.genActionsButtonsMarkup()}
            </x-actions-group>

          }
          <div slot="panelContent" class="body">
            {this.genNameMarkup()}
            <div class="collapse-expand-buttons">
              <x-button
                type="link"
                onClick={this.expandAll}
              >Expand All</x-button>
              <x-button
                type="link"
                onClick={this.collapseAll}
              >Collapse All</x-button>
            </div>
            <v-expansion-panels
              value={this.expandedCategories}
              multiple
              accordion
            >
              {this.getPermissionsStructure.map(
                (permissionCategory, index) => this.renderPermissionCategory(permissionCategory,
                  index),
              )}
            </v-expansion-panels>
          </div>
          {
            (!this.isPredefined && this.mode !== FormMode.ViewRole
              && ((this.userCanEditRoles && this.roleId)
                || (this.userCanAddRole && !this.roleId)))
              ? (
                <div slot="panelFooter">
                  <div className="buttons">
                    {
                      this.mode === FormMode.EditRole ? (
                        <x-button
                          type="link"
                          onClick={this.toggleEditMode}>Cancel</x-button>
                      ) : null
                    }
                    <x-button
                      type="primary"
                      onClick={this.saveRole}
                      disabled={this.isFormInvalid}
                    >Save</x-button>
                  </div>
                </div>) : null
          }
        </XSidePanel>
    );
  },
};
