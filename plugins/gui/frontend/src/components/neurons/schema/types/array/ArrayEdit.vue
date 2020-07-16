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
          class="x-multiple-select"
          mode="multiple"
          option-filter-prop="children"
          dropdown-class-name="x-multiple-select-dropdown"
          :get-popup-container="getPopupContainer"
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
    formatFieldName(validity) {
      let fieldName = validity.name;
      if (Array.isArray(this.schema.items)
              && this.schema.items.length > 1
              && this.schema.items[0].name === 'enabled'
              && this.schema.items[1].name === 'conditional') {
        const fileNameParts = fieldName.split('.');
        fileNameParts.splice(0, 1);
        fieldName = fileNameParts.join('.');
      }
      return fieldName;
    },
    addSchemaPrefix(validity) {
      let newValidity = null;
      if (Array.isArray(validity)) {
        newValidity = validity.map((fieldValidity) => ({ ...fieldValidity, name: `${this.schema.name}.${this.formatFieldName(fieldValidity)}` }));
      } else {
        newValidity = { ...validity, name: `${this.schema.name}.${this.formatFieldName(validity)}` };
      }
      return newValidity;
    },
    validate(silent, checkHiddenFields = false) {
      // If the user reverted his choice and decided not to fill a certain group of options,
      // We go through each of the children fields and make sure to invalidate them.
      // In other words, once the option sub fields is invisible again, we have to make them valid
      // since they are no longer relevant for validation.


      // handle a case where enable checkbox follow by conditional
      if (Array.isArray(this.schema.items)
                    && this.schema.items[0]
                    && this.schema.items[1]
                    && this.schema.items[0].name === 'enabled'
                    && this.schema.items.length > 1
                    && this.schema.items[0].name === 'enabled'
                    && this.schema.items[1].name === 'conditional') {
        const enabledItem = this.schema.items[0].name;
        const conditionalSelectedItem = this.schema.items[1].name;
        const conditionalEnumItems = this.schema.items[1].enum;

        // if form enabled then remove validation from drop down list unselected items ( hidden )
        if (this.data[enabledItem] === true) {
          const selected = this.data[conditionalSelectedItem];
          conditionalEnumItems.filter((item) => (item.name !== selected)).forEach((item) => {
            this.$emit('remove-validate',
              Object.keys(this.data[item.name])
                .map((conditionalItem) => ({ name: `${this.schema.name}.${conditionalItem}` })));
          });
          // if form is not enabled remove validate from all drop down list items
        } else {
          conditionalEnumItems.forEach((item) => {
            this.$emit('remove-validate', Object.keys(this.data[item.name])
              .map((mapItem) => ({ name: `${this.schema.name}.${mapItem}` })));
          });
        }
      }


      if (checkHiddenFields
           && this.schema.items[0].name === 'enabled'
           && this.data[this.schema.items[0].name] === false
           && this.schema.items.length > 1) {
        this.$emit('remove-validate', this.schema.items.slice(1)
          .map((item) => ({ name: `${this.schema.name}.${item.name}` })));
        return;
      }

      if (this.isStringList) {
        this.validateStringList(silent);
      } else if (this.$refs.itemChild) {
        this.$refs.itemChild.forEach((item) => item.validate(silent));
      }
    },
    addNewItem() {
      if (!this.schema.items.items) {
        this.data = [...this.data, null];
      } else {
        this.data = [...this.data,
          this.schema.items.items.reduce((map, field) => {
            // eslint-disable-next-line no-param-reassign
            map[field.name] = field.default || null;
            return map;
          }, {}),
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
      return document.querySelector('.x-array-edit');
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

      input, select, textarea {
        width: 100%;
      }

      .upload-file {
        margin-top: 8px;
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
      .x-multiple-select {
        width: 100%;
      }
    }
  }
</style>
