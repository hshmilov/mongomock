<template>
  <div class="x-entity-adapters">
    <x-tabs :vertical="true">
      <x-tab
        v-for="(item, i) in sortedSpecificData"
        :id="item.id"
        :key="i"
        :selected="!i"
        :disabled="item.outdated"
        :title="item.pretty_name || item.plugin_name"
        :logo="`adapters/${item.plugin_name}`"
      >
        <div class="d-flex content-header">
          <div class="flex-expand server-info">
            <template v-if="item.client_used">Data From: {{ item.client_used }}</template>
          </div>
          <x-button
            v-if="isGuiAdapterData(item)"
            @click="editFields"
          >Edit Fields</x-button>
          <x-button
            v-else
            link
            @click="toggleView"
          >View {{ viewBasic? 'advanced': 'basic' }}</x-button>
        </div>
        <x-list
          v-if="viewBasic || isGuiAdapterData(item)"
          :data="item"
          :schema="adapterSchema(item.plugin_name)"
        />
        <json-view
          v-else
          :data="item.data.raw"
          root-key="raw"
          :max-depth="6"
        />
      </x-tab>
    </x-tabs>
    <x-modal
      v-if="fieldsEditor.active"
      :disabled="!fieldsEditor.valid"
      approve-text="Save"
      @confirm="saveFieldsEditor"
      @close="closeFieldsEditor"
    >
      <x-custom-fields
        slot="body"
        v-model="fieldsEditor.data"
        :module="module"
        :fields="customFields"
        :external-error="error"
        @validate="validateFieldsEditor"
      />
    </x-modal>
    <x-toast
      v-if="toastMessage"
      v-model="toastMessage"
    />
  </div>

</template>

<script>
  import xTabs from '../../../axons/tabs/Tabs.vue'
  import xTab from '../../../axons/tabs/Tab.vue'
  import xList from '../../../neurons/schema/List.vue'
  import xButton from '../../../axons/inputs/Button.vue'
  import xModal from '../../../axons/popover/Modal.vue'
  import xCustomFields from './CustomFields.vue'
  import xToast from '../../../axons/popover/Toast.vue'
  import { JSONView } from "vue-json-component"

  import {mapState, mapMutations, mapActions} from 'vuex'
  import {SAVE_CUSTOM_DATA, FETCH_DATA_FIELDS} from '../../../../store/actions'
  import {CHANGE_TOUR_STATE} from '../../../../store/modules/onboarding'

  import {pluginMeta} from '../../../../constants/plugin_meta'
  import {guiPluginName, initCustomData} from '../../../../constants/entities'

  const lastSeenByModule = {
    'users': 'last_seen_in_devices',
    'devices': 'last_seen'
  }

  export default {
    name: 'XEntityAdapters',
    components: {
      xTabs, xTab, xList, xButton,
      xModal, xCustomFields, xToast,
      'json-view': JSONView
    },
    props: {
      entityId: {
        type: String,
        required: true
      },
      module: {
        type: String,
        required: true
      },
      adapters: {
        type: Array,
        default: () => []
      }
    },
    data() {
      return {
        viewBasic: true,
        fieldsEditor: {active: false},
        toastMessage: '',
        error: {}
      }
    },
    computed: {
      ...mapState({
        fields(state) {
          return state[this.module].fields.data
        }
      }),
      sortedSpecificData() {
        let lastSeen = new Set()
        let res = this.adapters.filter((item) => {
          if (item['hidden_for_gui']) return false
          if (item['plugin_type'] && item['plugin_type'].toLowerCase().includes('plugin')) return false

          return true
        }).sort((first, second) => {
          // GUI plugin (miscellaneous) always comes last
          if (first.plugin_name === guiPluginName) return 1
          if (second.plugin_name === guiPluginName) return -1

          // Adapters with no last_seen field go first
          let firstSeen = first.data[lastSeenByModule[this.module]]
          let secondSeen = second.data[lastSeenByModule[this.module]]
          if (!secondSeen) return 1
          if (!firstSeen) return -1
          // Turn strings into dates and subtract them to get a negative, positive, or zero value.
          return new Date(secondSeen) - new Date(firstSeen)
        }).map((item) => {
          item.id = `${item.plugin_unique_name}_${item.data.id}`
          if (pluginMeta[item.plugin_name]) {
            item.pretty_name = pluginMeta[item.plugin_name].title
          }
          if (lastSeen.has(item.plugin_name)) return {...item, outdated: true}
          lastSeen.add(item.plugin_name)
          return item
        })
        if (res.length === 0 || res[res.length - 1].plugin_name !== guiPluginName) {
          // Add initial gui adapters data
          res.push({
            ...initCustomData(this.module),
            pretty_name: pluginMeta[initCustomData(this.module).plugin_name].title
          })
        }
        return res
      },
      customFields () {
        return (this.fields.specific.gui || this.fields.generic)
      },
      customData () {
        return this.sortedSpecificData[this.sortedSpecificData.length - 1].data
      }
    },
    mounted() {
      if (this.module === 'devices') {
        this.$nextTick(() => {
          this.changeState({ name: 'adaptersData'})
        })
      }
    },
    methods: {
      ...mapMutations({
        changeState: CHANGE_TOUR_STATE
      }),
      ...mapActions({
        saveCustomData: SAVE_CUSTOM_DATA, fetchDataFields: FETCH_DATA_FIELDS,
      }),
      isGuiAdapterData(data) {
        return data.plugin_name === guiPluginName
      },
      adapterSchema(name) {
        if (!this.fields || !this.fields.schema) return {}
        let items = [{
          type: 'array', ...this.fields.schema.generic,
          name: 'data', title: 'SEPARATOR', path: [this.module, 'aggregator']
        }, {
          type: 'array', ...this.fields.schema.specific[name],
          name: 'data', title: 'SEPARATOR', path: [this.module, name]
        }]
        if (name === guiPluginName) {
          items[0].items = items[0].items.filter(item => item.name !== 'id')
        }
        return {type: 'array', items}
      },
      toggleView() {
        this.viewBasic = !this.viewBasic
      },
      editFields() {
        this.fieldsEditor = {
          active: true,
          data: Object.entries(this.customData).map(([ name, value ]) => {
            return { name, value, predefined: true }
          }),
          valid: true
        }
      },
      saveFieldsEditor() {
        if (!this.fieldsEditor.valid) return
        this.saveCustomData({
          module: this.module,
          selection: {
            ids: [this.entityId],
            include: true
          },
          data: this.fieldsEditor.data
        }).then(() => {
          this.toastMessage = 'Saved Custom Data'
          this.fetchDataFields({
            module: this.module
          })
          this.closeFieldsEditor()
        }).catch(error => {
          this.error = error.response.data.message
        })
      },
      closeFieldsEditor() {
        this.fieldsEditor = {active: false}
        this.error = {}
      },
      validateFieldsEditor(valid) {
        this.fieldsEditor.valid = valid
      },
    }
  }
</script>

<style lang="scss">
  .x-entity-adapters {
    .json-view-item {
      .data-key {
        padding: 2px;
      }
      .chevron-arrow {
        border-right-width: 2px;
        border-bottom-width: 2px;
      }
    }
  }
</style>