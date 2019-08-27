<template>
  <div class="x-field-config">
    <x-button
      link
      @click="isActive = true"
    >Edit Columns</x-button>
    <x-modal
      v-if="isActive"
      @close="isActive = false"
    >
      <template slot="body">
        <div class="x-field-filter">
          <x-select-symbol
            v-model="fieldType"
            :options="schema"
            :tabindex="1"
          />
          <x-search-input
            v-model="searchValue"
            :tabindex="2"
          />
        </div>
        <x-checkbox-list
          v-model="selectedFields"
          :items="currentFields"
        />
      </template>
      <template slot="footer">
        <x-button
          :tabindex="3"
          @click="isActive = false"
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
  import xButton from '../../axons/inputs/Button.vue'

  import { mapState, mapGetters, mapMutations } from 'vuex'
  import { GET_DATA_FIELDS_BY_PLUGIN } from '../../../store/getters'
  import { UPDATE_DATA_VIEW } from '../../../store/mutations'

  export default {
    name: 'XFieldConfig',
    components: { xModal, xSelectSymbol, xSearchInput, xCheckboxList, xButton },
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
      ...mapGetters({ getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN }),
      schema () {
        return this.getDataFieldsByPlugin(this.module)
      },
      selectedFields: {
        get () {
          return this.view.fields
        },
        set (fields) {
          this.updateView({
            module: this.module, view: { fields }
          })
          this.$emit('done')
        }
      },
      currentFields () {
        if (!this.schema || !this.schema.length) return []
        if (!this.fieldType) return this.schema[0].fields
        let fieldSchema = this.schema.find(item => item.name === this.fieldType)
        if (!fieldSchema) return []
        return fieldSchema.fields.filter((field) => {
          return field.title.toLowerCase().includes(this.searchValue.toLowerCase())
        })
      },
      firstType () {
        if (!this.schema || !this.schema.length) return 'axonius'
        return this.schema[0].name
      }
    },
    data () {
      return {
        isActive: false,
        fieldType: '',
        searchValue: ''
      }
    },
    watch: {
      firstType (newFirstType) {
        this.fieldType = newFirstType
      }
    },
    methods: {
      ...mapMutations({ updateView: UPDATE_DATA_VIEW })
    },
    created () {
      this.fieldType = this.firstType
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
            }
        }

        .x-select-trigger {
            color: $theme-black;
        }


        .x-field-filter {
            display: flex;

            .x-select-symbol {
                margin-right: 12px;
                flex-basis: 40%;
            }

            .x-search-input {
                flex: 1 0 auto;
            }
        }
    }
</style>
