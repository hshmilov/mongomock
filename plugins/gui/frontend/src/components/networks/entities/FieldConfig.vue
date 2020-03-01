<template>
  <XModal
    class="x-field-config"
    @close="closeModal"
  >
    <template slot="body">
      <div class="field-list stock">
        <h4 class="field-list__title">
          Available Columns
        </h4>
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
      <div class="actions">
        <XButton
          :disabled="!isStockSelected"
          @click="addFields"
        >Add &gt;&gt;</XButton>
        <XButton
          :disabled="!isViewSelected"
          @click="removeFields"
        >&lt;&lt; Remove</XButton>
        <XButton
          link
          :disabled="isDefaultViewFields"
          class="actions__reset"
          @click="reset"
        >Reset</XButton>
      </div>
      <div class="field-list view">
        <h4 class="field-list__title">
          Displayed Columns
        </h4>
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
    </template>
    <template slot="footer">
      <div class="modal-footer__save-default">
        <XButton
          link
          :disabled="isViewFieldsEmpty"
          @click="saveUserDefault"
        >Save as User Default</XButton>
      </div>
      <XButton
        link
        @click="closeModal"
      >Cancel</XButton>
      <XButton
        @click="onClickDone"
      >Done</XButton>
    </template>
  </XModal>
</template>

<script>
import { mapState, mapGetters, mapMutations } from 'vuex';
import { saveDefaultTableColumns } from '@api/user-preferences';
import _isEqual from 'lodash/isEqual';
import _isEmpty from 'lodash/isEmpty';

import XModal from '../../axons/popover/Modal.vue';
import XSelectSymbol from '../../neurons/inputs/SelectSymbol.vue';
import XSearchInput from '../../neurons/inputs/SearchInput.vue';
import XCheckboxList from '../../neurons/inputs/CheckboxList.vue';
import XTitle from '../../axons/layout/Title.vue';
import XButton from '../../axons/inputs/Button.vue';
import { GET_MODULE_SCHEMA, GET_DATA_SCHEMA_BY_NAME } from '../../../store/getters';
import { SHOW_TOASTER_MESSAGE, UPDATE_DATA_VIEW } from '../../../store/mutations';
import { getTypeFromField } from '../../../constants/utils';

export default {
  name: 'XFieldConfig',
  components: {
    XModal, XSelectSymbol, XSearchInput, XCheckboxList, XTitle, XButton,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    defaultFields: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    ...mapState({
      view(state) {
        return state[this.module].view;
      },
    }),
    ...mapGetters({
      getModuleSchema: GET_MODULE_SCHEMA,
      getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME,
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
      return fieldSchema.fields.filter((field) => !fieldDisplayed(field) && fieldSearched(field));
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
    isStockSelected() {
      return !_isEmpty(this.select.stock);
    },
    isViewSelected() {
      return !_isEmpty(this.select.view);
    },
    isDefaultViewFields() {
      return _isEqual(this.viewFields, this.defaultFields);
    },
    isViewFieldsEmpty() {
      return _isEmpty(this.viewFields);
    },
  },
  data() {
    return {
      viewFields: [],
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
    this.viewFields = this.view.fields;
    this.fieldType = this.firstType;
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    clearSelections() {
      this.select.view = [];
      this.select.stock = [];
    },
    closeModal() {
      this.$emit('close');
    },
    onClickDone() {
      this.updateView({
        module: this.module,
        view: {
          fields: this.viewFields,
        },
      });
      this.$emit('done');
      this.closeModal();
    },
    addFields() {
      this.viewFields = this.viewFields.concat(this.select.stock);
      this.select.stock = [];
      this.$nextTick(() => {
        const list = this.$refs.checklist.$el;
        list.scrollTop = list.scrollHeight;
      });
    },
    removeFields() {
      this.viewFields = this.viewFields.filter((field) => !this.select.view.includes(field));
      this.select.view = [];
    },
    reset() {
      this.viewFields = [...this.defaultFields];
      this.clearSelections();
    },
    updateViewFields(viewFieldsSchema) {
      this.viewFields = viewFieldsSchema.map((schema) => schema.name);
    },
    isFieldInSearch(field, searchValue) {
      return field.title.toLowerCase().includes(searchValue.toLowerCase());
    },
    resetSelectStock() {
      this.select.stock = [];
    },
    async saveUserDefault() {
      let message = 'Successfully saved user default view';
      try {
        await saveDefaultTableColumns(this.module, this.viewFields);
        this.$emit('update:default-fields', this.viewFields);
        this.onClickDone();
      } catch (error) {
        message = 'Error saving as default view';
      }
      this.showToasterMessage({
        message,
      });
    },
  },
};
</script>

<style lang="scss">
  .x-field-config {

    .modal-container {
      height: 500px;

      .modal-body {
        height: calc(100% - 40px);
        display: flex;
        align-items: center;

        .field-list {
          width: 40%;

          &__title {
            margin: 8px 0;
          }

          &__filter {
            display: flex;
            height: 32px;

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

        .actions {
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

      .modal-footer {
        display: flex;
        width: 100%;

        &__save-default {
          flex: 1 0 auto;
          text-align: left;

          .x-button {
            padding-left: 0;
          }
        }
      }
    }
  }
</style>
