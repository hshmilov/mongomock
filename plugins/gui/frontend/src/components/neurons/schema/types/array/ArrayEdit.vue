<template>
  <div class="x-array-edit">
    <template v-if="!isStringList">
      <Component
        :is="collapseType"
        :expand-icon-position="'right'"
        :bordered="false"
        default-active-key="1"
      >
        <Component
          :is="collapsePanelType"
          key="1"
          :header="schema.title"
        >
          <h4
            v-if="schema.title && !collapsible"
            :id="schema.name"
            :title="schema.description || ''"
            class="array-header"
          >{{ schema.title }}</h4>
          <Component
            :is="listWrapperType"
            v-model="data"
            ghost-class="ghost"
            class="list"
            :class="{ draggable }"
            @start="onStartDrag"
            @end="onEndDrag"
          >
            <div
              v-for="(item, index) in shownSchemaItems"
              :key="item.name"
              :class="`item item_${item.name}`"
            >
              <VIcon
                v-if="shownSchemaItems.length > 1 && draggable"
                size="15"
                class="draggable-expression-handle"
              >$vuetify.icons.draggable</VIcon>
              <XTypeWrap
                :name="item.name"
                :type="item.type"
                :title="item.title"
                :description="item.description"
                :required="item.required"
                :expand="!isFileList"
              >
                <Component
                  :is="item.type"
                  ref="itemChild"
                  :value="data[item.name]"
                  :schema="item"
                  :api-upload="apiUpload"
                  :read-only="readOnly"
                  @input="(value) => dataChanged(value, item.name)"
                  @validate="onValidate"
                  @remove-validate="onRemoveValidate"
                  :wrapping-class="wrappingClass"
                />
              </XTypeWrap>
              <XButton
                v-if="!isOrderedObject && !readOnly"
                type="link"
                class="remove-button"
                @click.prevent="removeItem(index)"
              >x</XButton>
            </div>
          </Component>
          <XButton
            v-if="!isOrderedObject && !readOnly"
            type="light"
            @click.prevent="addNewItem"
          >+</XButton>
        </Component>
      </Component>
    </template>
    <template v-else-if="isStringList && schema.items.enum">
      <AFormItem
        :help="schema.placeholder ? schema.placeholder : null"
        :label="schema.title"
      >
        <ASelect
          :id="`${schema.name}_select`"
          v-model="data"
          :class="`x-multiple-select ${schema.name}_select`"
          mode="multiple"
          option-filter-prop="children"
          dropdown-class-name="x-multiple-select-dropdown"
          :get-popup-container="getPopupContainer"
          :disabled="readOnly"
        >
          <ASelectOption
            v-for="item in schema.items.enum"
            :key="item.name"
          >
            {{ item.title }}
          </ASelectOption>
        </ASelect>
      </AFormItem>
    </template>
    <template v-else>
      <label>{{ schema.title }}</label>
      <XListInput
        :id="schema.name"
        v-model="data"
        :format="formatStringItem"
        :error-items="invalidStringItems"
        :class="{'error-border': !stringListValid}"
        :read-only="readOnly"
        @focusout.native="() => validateStringList()"
      />
    </template>
  </div>
</template>

<script>
import { Collapse, Form, Select } from 'ant-design-vue';
import draggable from 'vuedraggable';
import XTypeWrap from './TypeWrap.vue';
import string from '../string/StringEdit.vue';
import number from '../numerical/NumberEdit.vue';
import integer from '../numerical/IntegerEdit.vue';
import bool from '../boolean/BooleanEdit.vue';
import file from './FileEdit.vue';
import range from '../string/RangeEdit.vue';
import XButton from '../../../../axons/inputs/Button.vue';
import XListInput from '../../../../axons/inputs/ListInput.vue';
import { validateEmail } from '../../../../../constants/validations';
import arrayMixin from '../../../../../mixins/array';

const vault = () => import('../string/VaultEdit.vue');

const { Panel } = Collapse;

export default {
  name: 'Array',
  components: {
    Collapse,
    Panel,
    XTypeWrap,
    string,
    number,
    integer,
    bool,
    file,
    range,
    XButton,
    XListInput,
    vault,
    draggable,
    ASelect: Select,
    ASelectOption: Select.Option,
    AFormItem: Form.Item,
  },
  mixins: [arrayMixin],
  props: {
    readOnly: {
      type: Boolean,
      default: false,
    },
    useVault: {
      type: Boolean,
      default: false,
    },
    wrappingClass: {
      type: String,
      default: null,
    },
  },
  data() {
    return {
      needsValidation: false,
      stringListValid: true,
      dragging: false,
    };
  },
  computed: {
    draggable() {
      return this.schema.ordered;
    },
    collapsible() {
      return this.schema.collapsible;
    },
    orderedItems: {
      get() {
        return this.shownSchemaItems || [];
      },
      set(newItems) {
        this.$emit('change', newItems);
      },
    },
    isStringList() {
      if (this.isOrderedObject) return false;
      return this.schema.items.type === 'string';
    },
    isFileList() {
      if (this.isOrderedObject) return false;
      return this.schema.items.type === 'file';
    },
    invalidStringItems() {
      if (!this.isStringList) return [];
      return this.data.filter((item) => {
        if (this.schema.items.format === 'email') {
          return !validateEmail(item);
        }
        return false;
      });
    },
    stringListError() {
      if (this.invalidStringItems.length) {
        return `'${this.schema.title}' items are not all properly formed`;
      } if (this.data.length === 0 && this.schema.required) {
        return `'${this.schema.title}' is required`;
      }
      return '';
    },
    listWrapperType() {
      return this.draggable ? 'draggable' : 'div';
    },
    collapseType() {
      return this.collapsible ? 'Collapse' : 'div';
    },
    collapsePanelType() {
      return this.collapsible ? 'Panel' : 'div';
    },
  },
  watch: {
    isHidden() {
      /*
      Change of hidden, means some fields may appear or disappear.
      Therefore, the new children should be re-validated but the DOM has not updated yet
      */
      this.needsValidation = true;
    },
    stringListError() {
      this.validateStringList();
    },
  },
  mounted() {
    this.validate(true);
    // When loaded, update data with default values, as defined
    let updateData = false;
    this.schemaItems.forEach((item) => {
      if (item.type === 'array') {
        // An array, no need to handle recursively
        return;
      }
      if (this.data[item.name] !== undefined && this.data[item.name] !== null && !this.useVault) {
        // Value exists, no need to process
        return;
      }
      if (item.type === 'bool') {
        this.data[item.name] = false;
        updateData = true;
      }
      if (item.format && item.format === 'password' && this.useVault) {
        item.type = 'vault';
      }
      if (!item.default) {
        // Nothing defined to set
        return;
      }

      this.data[item.name] = item.default;
      updateData = true;
    });
    if (updateData) {
      this.data = { ...this.data };
    }
  },
  updated() {
    if (this.needsValidation) {
      // Here the new children (after change of hidden) are updated in the DOM
      this.validate(true, true);
      this.needsValidation = false;
    }
  },
  methods: {
    dataChanged(value, itemName) {
      if (itemName === 'conditional') {
        this.needsValidation = true;
      }
      if (Array.isArray(this.data) && typeof itemName === 'number') {
        this.data = this.data.map((item, index) => (index === itemName ? value : item));
      } else {
        this.data = { ...this.data, [itemName]: value };
      }
    },
    onValidate(validity) {
      this.$emit('validate', this.addSchemaPrefix(validity));
    },
    onRemoveValidate(validity) {
      this.$emit('remove-validate', this.addSchemaPrefix(validity));
    },
    addSchemaPrefix(validity) {
      if (!this.schema.name) {
        return validity;
      }
      if (Array.isArray(validity)) {
        return validity.map((fieldValidity) => ({
          ...fieldValidity,
          name: `${this.schema.name}.${fieldValidity.name}`,
        }));
      }
      return { ...validity, name: `${this.schema.name}.${validity.name}` };
    },
    validate(silent) {
      if (this.isStringList) {
        this.validateStringList(silent);
        return;
      }
      if (!this.$refs.itemChild) {
        return;
      }
      const activeFieldNames = this.$refs.itemChild.map((ref) => ref.schema.name);
      const isFieldHidden = (field) => !activeFieldNames.includes(field.name);
      const isFieldRecursible = (field) => (field.items && Array.isArray(field.items));
      const getHiddenFields = (fields, path) => fields.filter(isFieldHidden)
        .reduce((hiddenFields, currentField) => {
          const name = path ? `${path}.${currentField.name}` : currentField.name;
          if (isFieldRecursible(currentField)) {
            return [...hiddenFields, ...getHiddenFields(currentField.items, name)];
          }
          return [...hiddenFields, { name }];
        }, []);
      this.$emit('remove-validate', getHiddenFields(this.schema.items, this.schema.name));
      this.$refs.itemChild.forEach((item) => item.validate(silent));
    },
    addNewItem() {
      if (!this.schema.items.items || this.schema.items.type === 'file') {
        this.data = [...this.data, null];
      } else {
        this.data = [...this.data,
          this.schema.items.items.reduce((map, field) => ({
            ...map,
            [field.name]: field.default || null,
          }), {}),
        ];
      }
    },
    removeItem(index) {
      this.data.splice(index, 1);
      this.$emit('remove-validate', this.schema.items.items
        .map((item) => ({ name: `${this.schema.name}.${index}.${item.name}` })));
    },
    formatStringItem(item) {
      if (this.schema.items.format === 'email') {
        const emailMatch = item.match(new RegExp('.*?s?<(.*?)>'));
        if (emailMatch && emailMatch.length > 1) {
          return emailMatch[1];
        }
      }
      return item;
    },
    validateStringList(silent) {
      const valid = this.stringListError === '';
      this.stringListValid = valid || silent;
      this.$emit('validate', {
        name: this.schema.name,
        valid,
        error: this.stringListValid ? '' : this.stringListError,
      });
    },
    onStartDrag() {
      this.dragging = true;
    },
    onEndDrag() {
      this.dragging = false;
    },
    getPopupContainer() {
      const selector = this.wrappingClass ? `.${this.wrappingClass} .x-array-edit` : '.x-array-edit';
      return document.querySelector(selector);
    },
  },
};
</script>

<style lang="scss">
  .x-array-edit {
    position: relative;
    .v-text-field > .v-input__control > .v-input__slot:before {
      border-style: none;
      border-width: thin 0 0;
    }
    .v-text-field > .v-input__control > .v-input__slot:after {
      border-style: none;
      border-width: thin 0 0;
    }
    .v-text-field > .v-input__control > .v-input__slot:hover {
      border-style: none;
      border-width: thin 0 0;
    }
    .array-header {
      margin-bottom: 0;
      display: inline-block;
      min-width: 200px;
    }
    .item {
      display: flex;
      align-items: flex-end;

      .ant-collapse-borderless > .ant-collapse-item {
        border-style: none;
        .anticon.anticon-right.ant-collapse-arrow {
          right: 0;
          left: auto;
        }
        .ant-collapse-header {
          padding: 0 42px 0 0;
        }
        .ant-collapse-content > .ant-collapse-content-box {
          padding: 0;
        }
        .object {
          margin-top: 0;
        }
      }

      .list.draggable {
        .list {
          display: flex;
          justify-content: space-between;
          margin-top: 10px;

          .item {
            label {
              display: none;
            }
            .string-input-container {
              input {
                height: 32px;
                line-height: 30px;
                border-radius: 2px;
                border: 1px solid $grey-2;
                background: $grey-dient;
                padding-left: 4px;
              }
            }

            width: 150px;
          }
        }
      }

      .draggable-expression-handle {
        float: left;
        cursor: move;
        margin-right: 4px;
        margin-bottom: 8px;
        width: 5%;
      }

      .index {
        display: inline-block;
        vertical-align: top;
      }

      .x-button {
        &.ant-btn-link {
          text-align: right;
        }
        &.ant-btn-light {
          margin-top: 8px;
          display: block;
        }
      }
    }

    .object {
      display: inline-block;
      width: auto;
      margin-top: 8px;

      &.expand {
        width: 100%;
      }

      input, select, textarea {
        width: 100%;
      }
    }

    .v-select.v-autocomplete {
      input {
        border-style: none;
      }
    }

    .ant-form-item {
      grid-column: 1/-1;
      margin-bottom: 0;

      &-label {
        line-height: initial;
        label::after {
          content: '';
        }
      }

      .x-multiple-select {
        width: 100%;
      }
    }

    .v-text-field {
      padding-top: 0;
      margin-top: 0;
      .v-text-field__details, .v-messages {
        min-height: 0;
      }
    }

    .item_conditional .x-dropdown {
      width: 200px;
    }
  }
</style>
