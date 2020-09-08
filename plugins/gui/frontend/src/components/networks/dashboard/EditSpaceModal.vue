<template>
  <AModal
    class="edit-space-modal"
    :visible="true"
    :centered="true"
    :closable="false"
    :width="null"
    :cancel-button-props="{ props: { type: 'link' } }"
    :ok-button-props="{ props: { disabled: !formValid }}"
    :mask-closable="false"
    ok-text="Save"
    :title="formTitle"
    @ok="submitEdit"
    @cancel="$emit('cancel')"
  >
    <AForm
      layout="vertical"
    >
      <AFormItem
        label="Space name"
      >
        <AInput
          id="rename_space"
          ref="nameInput"
          v-model="spaceForm.name"
          @pressEnter="submitEdit"
        />
      </AFormItem>
      <template
        v-if="allowRoleSelection"
      >
        <AFormItem
          label="Space access"
        >
          <ARadioGroup
            v-model="spaceForm.public"
            :disabled="!canViewUsersAndRoles"
          >
            <ARadio
              id="public_space_access"
              :value="true"
            >
              Public
            </ARadio>
            <ARadio
              id="roles_space_access"
              :value="false"
            >
              Roles
            </ARadio>
          </ARadioGroup>
        </AFormItem>
        <AFormItem
          v-if="!spaceForm.public && canViewUsersAndRoles"
          help="Admin role will always have access. Leave empty for Admin access only."
        >
          <ASelect
            id="select_space"
            v-model="spaceForm.roles"
            class="x-multiple-select"
            mode="multiple"
            :max-tag-count="5"
            option-filter-prop="children"
            dropdown-class-name="x-multiple-select-dropdown"
          >
            <ASelectOption
              v-for="option in rolesOptions"
              :key="option.value"
            >
              {{ option.text }}
            </ASelectOption>
          </ASelect>
        </AFormItem>
      </template>
    </AForm>
  </AModal>
</template>

<script>
import {
  Modal, Input, Radio, Form, Select,
} from 'ant-design-vue';
import _pick from 'lodash/pick';
import _isEmpty from 'lodash/isEmpty';
import { fetchAssignableRolesList } from '@api/roles';
import { SpaceTypesEnum } from '@constants/dashboard';

export default {
  name: 'XEditSpaceModal',
  components: {
    AModal: Modal,
    AInput: Input,
    ARadio: Radio,
    ARadioGroup: Radio.Group,
    AForm: Form,
    AFormItem: Form.Item,
    ASelect: Select,
    ASelectOption: Select.Option,
  },
  props: {
    space: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      rolesOptions: [],
      error: '',
      spaceForm: false,
    };
  },
  computed: {
    canViewUsersAndRoles() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.GetUsersAndRoles);
    },
    isNewSpace() {
      return _isEmpty(this.space);
    },
    allowRoleSelection() {
      return this.space.type === SpaceTypesEnum.custom || this.isNewSpace;
    },
    formTitle() {
      return this.isNewSpace ? 'New Space' : 'Edit Space';
    },
    formValid() {
      return this.spaceForm.name;
    },
  },
  async created() {
    if (this.canViewUsersAndRoles) {
      const allRoles = await fetchAssignableRolesList();
      this.rolesOptions = allRoles.filter((option) => option.text !== 'Admin');
    }
    this.fillDataFromSpace(this.space);
  },
  mounted() {
    this.focusInput();
  },
  methods: {
    fillDataFromSpace(space) {
      this.spaceForm = {
        id: space.uuid,
        name: '',
        roles: [],
        public: true,
        ..._pick(space, ['name', 'roles', 'public']),
      };
    },
    submitEdit() {
      if (!this.spaceForm.name) return;
      this.$emit('confirm', this.spaceForm);
    },
    focusInput() {
      const ref = this.$refs.nameInput;
      ref.focus();
    },
  },
};
</script>

<style lang="scss">
.edit-space-modal {
  width: 490px;
  .ant-form-item {
    margin-bottom: 0;
  }
  form input[type='radio'] {
    width: 16px;
    height: 16px;
  }
}
</style>
