<template>
  <div>
    <x-dropdown
      ref="dropdown"
      size="sm"
      align="right"
      :arrow="false"
    >
      <x-button
        slot="trigger"
        link
      >Actions</x-button>
      <x-menu slot="content">
        <x-menu-item
          v-for="item in $children"
          v-if="item.title"
          :key="item.title"
          :title="item.title"
          @click="activate(item)"
        />
      </x-menu>
    </x-dropdown>
    <x-tag-modal
      title="Tag..."
      :module="module"
      :entities="entities"
      :entities-meta="entitiesMeta"
      @done="() => $emit('done', false)"
    />
    <x-action-menu-item
      title="Delete..."
      :handle-save="deleteEntities"
      :message="`Deleted ${module}`"
      action-text="Delete"
    >
      <div class="warn-delete">You are about to delete {{ selectionCount }} {{ module }}.</div>
      <div>These {{ module }} could reappear in further scans if they are not removed or detached.</div>
      <div>Are you sure you want to delete these {{ module }}?</div>
    </x-action-menu-item>
    <slot />
    <x-action-menu-item
      :title="`Add custom data...`"
      :handle-save="saveFields"
      :message="`Custom data saved`"
      action-text="Save"
    >
      <x-custom-fields
        v-model="customAdapterData"
        :module="module"
        :fields="fields"
      />
    </x-action-menu-item>
  </div>
</template>

<script>
  import xDropdown from '../../axons/popover/Dropdown.vue'
  import xMenu from '../../axons/menus/Menu.vue'
  import xMenuItem from '../../axons/menus/MenuItem.vue'
  import xActionMenuItem from './ActionMenuItem.vue'
  import xTagModal from '../popover/TagModal.vue'
  import xCustomFields from '../../networks/entities/view/CustomFields.vue'
  import xButton from '../../axons/inputs/Button.vue'

  import { mapState, mapActions } from 'vuex'
  import { DELETE_DATA, DISABLE_DATA, SAVE_CUSTOM_DATA } from '../../../store/actions'

  export default {
    name: 'XActionMenu',
    components: {
      xDropdown, 'x-menu': xMenu, 'x-menu-item': xMenuItem,
      xActionMenuItem, xTagModal, xCustomFields, xButton
    },
    props: {
      module: {
        type: String,
        required: true
      },
      entities: {
        type: Object,
        required: true
      },
      entitiesMeta: {
        type: Object,
        default: () => {}
      }
    },
    data () {
      return {
        customAdapterData: { id: 'unique' }
      }
    },
    computed: {
      ...mapState({
        dataCount (state) {
          return state[this.module].count.data
        },
        fields (state) {
          let fields = state[this.module].fields.data
          if (!fields) return []
          if (!fields.specific) return fields.generic
          return fields.specific.gui || fields.generic
        }
      }),
      selectionCount () {
        if (this.entities.include === undefined || this.entities.include) {
          return this.entities.ids.length
        }
        return this.dataCount - this.entities.ids.length
      }
    },
    methods: {
      ...mapActions({
        disableData: DISABLE_DATA,
        deleteData: DELETE_DATA,
        saveCustomData: SAVE_CUSTOM_DATA
      }),
      activate (item) {
        if (!item || !item.activate) return
        item.activate()
        this.$el.click()
        this.$refs.dropdown.close()
      },
      deleteEntities () {
        return this.deleteData({
          module: this.module, selection: this.entities
        }).then(() => this.$emit('done'))
      },
      saveFields () {
        return this.saveCustomData({
          module: this.module, data: {
            selection: this.entities, data: this.customAdapterData
          }
        })
      }
    }
  }
</script>

<style lang="scss">

</style>