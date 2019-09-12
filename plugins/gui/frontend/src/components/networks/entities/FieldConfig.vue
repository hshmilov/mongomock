<template>
  <div class="x-field-config">
    <x-button
      link
      @click="openModal"
    >Edit Columns</x-button>
    <x-modal
      v-if="isActive"
      @close="closeModal"
    >
      <template slot="body">
        <div class="field-list stock">
          <h4 class="field-list__title">Available Columns</h4>
          <div class="field-list__filter">
            <x-select-symbol
              v-model="fieldType"
              :options="schemaByPlugin"
              minimal
              :tabindex="1"
            />
            <x-search-input v-model="search.stock" />
          </div>
          <x-checkbox-list
            v-model="select.stock"
            :items="stockFieldsSchema"
          />
        </div>
        <div class="actions">
          <x-button
            :disabled="!isStockSelected"
            @click="addFields"
          >Add &gt;&gt;</x-button>
          <x-button
            :disabled="!isViewSelected"
            @click="removeFields"
          >&lt;&lt; Remove</x-button>
          <x-button
            link
            :disabled="!viewFields.length"
            @click="removeAll"
          >Remove All</x-button>
        </div>
        <div class="field-list view">
          <h4 class="field-list__title">Displayed Columns</h4>
          <div class="field-list__filter">
            <x-search-input v-model="search.view" />
          </div>
          <x-checkbox-list
            v-model="select.view"
            :items="viewFieldsSchema"
            :draggable="true"
            @change="updateViewFields"
          >
            <x-title
              slot-scope="{ item }"
              :logo="item.logo"
              :height="16"
            >{{ item.title }}</x-title>
          </x-checkbox-list>
        </div>
      </template>
      <template slot="footer">
        <x-button
          link
          @click="closeModal"
        >Cancel</x-button>
        <x-button
          @click="onClickDone"
        >Done</x-button>
      </template>
    </x-modal>
  </div>
</template>

<script>
  import xModal from '../../axons/popover/Modal.vue'
  import xSelectSymbol from '../../neurons/inputs/SelectSymbol.vue'
  import xSearchInput from '../../neurons/inputs/SearchInput.vue'
  import xCheckboxList from '../../neurons/inputs/CheckboxList.vue'
  import xTitle from '../../axons/layout/Title.vue'
  import xButton from '../../axons/inputs/Button.vue'

  import { mapState, mapGetters, mapMutations } from 'vuex'
  import { GET_DATA_FIELDS_BY_PLUGIN, GET_DATA_SCHEMA_BY_NAME } from '../../../store/getters'
  import { UPDATE_DATA_VIEW } from '../../../store/mutations'
  import { getTypeFromField } from '../../../constants/utils'

  export default {
    name: 'XFieldConfig',
    components: { xModal, xSelectSymbol, xSearchInput, xCheckboxList, xTitle, xButton },
    props: {
      module: {
        type: String,
        required: true
      }
    },
    computed: {
      ...mapState({
        view (state) {
          return state[this.module].view
        }
      }),
      ...mapGetters({
        getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN,
        getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME
      }),
      schemaByPlugin () {
        return this.getDataFieldsByPlugin(this.module)
      },
      schemaByName () {
        return this.getDataSchemaByName(this.module)
      },
      stockFieldsSchema () {
        if (!this.schemaByPlugin || !this.schemaByPlugin.length) {
          return []
        }
        if (!this.fieldType) {
          return this.schemaByPlugin[0].fields
        }
        let fieldSchema = this.schemaByPlugin.find(item => item.name === this.fieldType)
        if (!fieldSchema) {
          return []
        }
        return fieldSchema.fields.filter(field => !this.viewFields.includes(field.name) && this.isFieldInSearch(field, this.search.stock))
      },
      viewFieldsSchema () {
        let schemaByName = this.schemaByName
        return this.viewFields
                .map(fieldName => {
                  return {
                    ...schemaByName[fieldName], logo: `adapters/${getTypeFromField(fieldName)}`
                  }
                }).filter(field => this.isFieldInSearch(field, this.search.view))
      },
      firstType () {
        if (!this.schemaByPlugin || !this.schemaByPlugin.length) return 'axonius'
        return this.schemaByPlugin[0].name
      },
      isStockSelected () {
        return this.select.stock.length > 0
      },
      isViewSelected () {
        return this.select.view.length > 0
      }
    },
    data () {
      return {
        isActive: false,
        viewFields: [],
        select: {
          stock: [],
          view: []
        },
        search: {
          stock: '',
          view: ''
        },
        fieldType: ''
      }
    },
    methods: {
      ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
      openModal () {
        this.isActive = true
        this.viewFields = this.view.fields
        this.fieldType = this.firstType
      },
      closeModal () {
        this.isActive = false
      },
      onClickDone () {
        this.updateView({
          module: this.module,
          view: {
            fields: this.viewFields
          }
        })
        this.$emit('done')
        this.closeModal()
      },
      addFields () {
        this.viewFields = this.viewFields.concat(this.select.stock)
        this.select.stock = []
      },
      removeFields () {
        this.viewFields = this.viewFields.filter(field => !this.select.view.includes(field))
        this.select.view = []
      },
      removeAll () {
        this.viewFields = []
      },
      updateViewFields (viewFieldsSchema) {
        this.viewFields = viewFieldsSchema.map(schema => schema.name)
      },
      isFieldInSearch (field, searchValue) {
        return field.title.toLowerCase().includes(searchValue.toLowerCase())
      }
    }
  }
</script>

<style lang="scss">
  .x-field-config {

    > .x-button {
      width: 120px;
    }

    .x-modal .modal-container {
      height: 500px;

      .modal-body {
        height: calc(100% - 40px);
        display: flex;
        align-items: center;

        .field-list {
          flex-basis: 40%;
          width: 40%;

          &__title {
            margin: 8px 0;
          }

          &__filter {
            display: flex;

            .x-search-input {
              width: 100%;
            }
          }

          .x-checkbox-list {
            height: 360px;
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
                  width: calc(100% - 24px);
                  white-space: nowrap;
                  text-overflow: ellipsis;
                  overflow: hidden;

                  .text {
                    margin-left: 4px;
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

            &:last-of-type {
              margin-bottom: 0;
            }
          }
        }
      }
    }
  }
</style>
