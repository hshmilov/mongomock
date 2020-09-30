<template>
  <AModal
    :visible="true"
    :closable="false"
    width="770px"
    :centered="true"
    :title="title"
    class="x-edit-columns-modal"
    @cancel="closeModal"
  >
    <div class="modal-body">
      <div class="field-list stock">
        <div class="field-list__title">
          Available Columns
        </div>
        <div class="field-list__filter">
          <XSelectSymbol
            v-model="fieldType"
            :options="schemaByPlugin"
            minimal
            :tabindex="1"
            @input="resetSelectStock"
          />
          <XSearchInput v-model="search.stock" />
        </div>
        <XCheckboxList
          v-model="select.stock"
          :items="stockFieldsSchema"
        />
      </div>
      <div class="modal-body__actions">
        <XButton
          type="primary"
          :disabled="!isStockSelected"
          @click="addFields"
        >Add &gt;&gt;</XButton>
        <XButton
          type="primary"
          :disabled="!isViewSelected"
          @click="removeFields"
        >&lt;&lt; Remove</XButton>
        <XButton
          type="link"
          :disabled="isDefaultViewFields"
          class="actions__reset"
          @click="reset"
        >Reset</XButton>
      </div>
      <div class="field-list view">
        <div class="field-list__title">
          Displayed Columns
        </div>
        <div class="field-list__filter">
          <XSearchInput v-model="search.view" />
        </div>
        <XCheckboxList
          ref="checklist"
          v-model="select.view"
          :items="viewFieldsSchema"
          :draggable="true"
          @change="updateViewFields"
        >
          <XTitle
            slot-scope="{ item }"
            :logo="item.logo"
            :height="16"
          >{{ item.title }}</XTitle>
        </XCheckboxList>
      </div>
    </div>

    <template #footer>
      <div class="ant-modal-footer__save-default">
        <slot name="extraActions" />
      </div>
      <XButton
        type="link"
        @click="closeModal"
      >Cancel</XButton>
      <XButton
        type="primary"
        @click="$emit('approve')"
      >{{ approveText }}</XButton>
    </template>
  </AModal>
</template>

<script>
import { mapGetters } from 'vuex';
import _get from 'lodash/get';
import _isEqual from 'lodash/isEqual';
import _isEmpty from 'lodash/isEmpty';
import _snakeCase from 'lodash/snakeCase';
import { Modal } from 'ant-design-vue';
import XSelectSymbol from '../../neurons/inputs/SelectSymbol.vue';
import XSearchInput from '../../neurons/inputs/SearchInput.vue';
import XCheckboxList from '../../neurons/inputs/CheckboxList.vue';
import XTitle from '../../axons/layout/Title.vue';
import {
  GET_MODULE_SCHEMA,
  GET_DATA_SCHEMA_BY_NAME,
  FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES,
} from '../../../store/getters';
import { getTypeFromField } from '../../../constants/utils';

export default {
  name: 'XEditColumnsModal',
  components: {
    AModal: Modal,
    XSelectSymbol,
    XSearchInput,
    XCheckboxList,
    XTitle,
  },
  props: {
    title: {
      type: String,
      required: true,
    },
    currentFields: {
      type: Array,
      required: true,
    },
    approveText: {
      type: String,
      required: true,
    },
    module: {
      type: String,
      required: true,
    },
    userFieldsGroups: {
      type: Object,
      default: () => ({}),
    },
  },
  computed: {
    ...mapGetters({
      getModuleSchema: GET_MODULE_SCHEMA,
      getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME,
      fillUserFieldGroups: FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES,
    }),
    schemaByPlugin() {
      return this.getModuleSchema(this.module);
    },
    schemaByName() {
      return this.getDataSchemaByName(this.module);
    },
    stockFieldsSchema() {
      if (!this.schemaByPlugin || !this.schemaByPlugin.length) {
        return [];
      }
      if (!this.fieldType) {
        return this.schemaByPlugin[0].fields;
      }
      const fieldSchema = this.schemaByPlugin.find((item) => item.name === this.fieldType);
      if (!fieldSchema) {
        return [];
      }
      const fieldDisplayed = (field) => this.viewFields.includes(field.name);
      const fieldSearched = (field) => this.isFieldInSearch(field, this.search.stock);
      // adapter_count (Distinct Adapter Connections Count) is a dynamic field per device, therefore we dont allow it as column
      const fieldExcluded = (field) => this.excludedFields.includes(field.name) || field.name.endsWith('adapter_count');
      return fieldSchema.fields.filter((field) => !fieldDisplayed(field) && fieldSearched(field) && !fieldExcluded(field));
    },
    viewFieldsSchema() {
      const { schemaByName } = this;
      return this.viewFields
        .map((fieldName) => (!schemaByName[fieldName] ? null : {
          ...schemaByName[fieldName], logo: `adapters/${getTypeFromField(fieldName)}`,
        })).filter((field) => field && this.isFieldInSearch(field, this.search.view));
    },
    firstType() {
      if (!this.schemaByPlugin || !this.schemaByPlugin.length) return 'axonius';
      return this.schemaByPlugin[0].name;
    },
    querySearchTemplate() {
      return _get(this.view, 'query.meta.searchTemplate', false);
    },
    isStockSelected() {
      return !_isEmpty(this.select.stock);
    },
    isViewSelected() {
      return !_isEmpty(this.select.view);
    },
    isDefaultViewFields() {
      let defaultFields = this.userFieldsGroups.default;
      if (this.querySearchTemplate) {
        const allFieldsGroup = this.fillUserFieldGroups(this.module, this.userFieldsGroups);
        defaultFields = allFieldsGroup[_snakeCase(this.querySearchTemplate.name)];
      }
      return _isEqual(this.viewFields, defaultFields);
    },
  },
  data() {
    return {
      viewFields: [],
      excludedFields: ['adapter_list_length', 'specific_data.data.correlation_reasons'],
      select: {
        stock: [],
        view: [],
      },
      search: {
        stock: '',
        view: '',
      },
      fieldType: '',
    };
  },
  created() {
    this.viewFields = this.currentFields;
    this.fieldType = this.firstType;
  },
  methods: {
    clearSelections() {
      this.select.view = [];
      this.select.stock = [];
    },
    closeModal() {
      this.$emit('close');
    },
    addFields() {
      this.viewFields = this.viewFields.concat(this.select.stock);
      this.select.stock = [];
      this.$nextTick(() => {
        const list = this.$refs.checklist.$el;
        list.scrollTop = list.scrollHeight;
      });
      this.$emit('update-unsaved-fields', this.viewFields);
    },
    removeFields() {
      this.viewFields = this.viewFields.filter((field) => !this.select.view.includes(field));
      this.select.view = [];
      this.$emit('update-unsaved-fields', this.viewFields);
    },
    reset() {
      this.$emit('reset-user-fields');
      this.viewFields = [...this.currentFields];
      this.clearSelections();
    },
    updateViewFields(viewFieldsSchema) {
      this.viewFields = viewFieldsSchema.map((schema) => schema.name);
      this.$emit('update-unsaved-fields', this.viewFields);
    },
    isFieldInSearch(field, searchValue) {
      return field.title.toLowerCase().includes(searchValue.toLowerCase());
    },
    resetSelectStock() {
      this.select.stock = [];
    },
  },
};
</script>

<style lang="scss">
  .x-edit-columns-modal {

      .modal-body {
        display: flex;
        align-items: center;

        .field-list {
          width: 40%;

          &__title {
            font-weight: 300;
            font-size: 16px;
            margin-bottom: 8px;
          }

          &__filter {
            display: flex;
            height: 32px;

            .x-select {
              border-right: 0;
              border-radius: 0;
            }

            .x-search-input {
              width: 100%;
            }
          }

          .x-checkbox-list {
            border: 1px solid $grey-2;
            padding: 8px 0;

            .list {
              grid-template-columns: 1fr;

              .x-checkbox {
                display: flex;
                align-items: center;
                padding: 0 8px;

                .x-title, .label {
                  margin-left: 8px;
                  white-space: nowrap;

                  .text {
                    margin-left: 4px;
                    text-overflow: initial;
                    overflow: initial;
                  }
                }
              }
            }
          }
        }

        &__actions {
          display: flex;
          flex-direction: column;
          margin: 0 8px;

          .x-button {
            margin-bottom: 4px;
          }

          &__reset {
            margin-bottom: 0;
            padding: 0;
          }
        }
      }

      .ant-modal-footer {
        margin-top: 26px;
        display: flex;
        width: 100%;

        &__save-default {
          flex: 1 0 auto;
          text-align: left;
        }

      }
  }
  /* This is an ad-hoc solution for ticket AX-7879 and the regression it casused*/
  @media (max-height: 700px) {
      .x-edit-columns-modal > .modal-container {
        .modal-body {
          height: unset;
          align-items: unset;
          &__actions {
            justify-content: center;
            align-items: unset;
          }
        }
      }
    }
</style>
