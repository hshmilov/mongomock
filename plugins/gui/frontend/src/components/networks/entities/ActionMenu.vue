<template>
  <x-action-menu
    :module="module"
    :entities="entities"
    :entities-meta="entitiesMeta"
    @done="(reset) => $emit('done', reset)"
  >
    <x-action-menu-item
      :title="`Link ${module}`"
      :handle-save="linkEntities"
      :message="`${module} were linked`"
      action-text="Save"
      :disabled="selectionCount > 10"
    >
      <div
        v-if="selectionCount > 10"
        class="error"
      >Maximal amount of {{ module }} to link is 10</div>
      <div
        v-else
        class="warn-delete"
      >You are about to link {{ selectionCount }} {{ module }}.</div>
    </x-action-menu-item>
    <x-action-menu-item
      :title="`Unlink ${module}`"
      :handle-save="unlinkEntities"
      :message="`${module} were unlinked`"
      action-text="Save"
    >
      <div class="warn-delete">You are about to unlink {{ selectionCount }} {{ module }}. This means that each of the adapter {{ module }} inside will become a standalone axonius entity.</div>
    </x-action-menu-item>
    <x-action-menu-item
      v-if="!enforcementRestricted"
      title="Enforce"
      :handle-save="enforceEntities"
      :message="`Enforcement is running. View in Enforcements -> Tasks`"
      action-text="Run"
    >
      <div class="mb-8">There are {{ selectionCount }} {{ module }} selected. Select the Enforcement Set:</div>
      <x-select v-model="selectedEnforcement" :options="enforcementOptions"></x-select>
    </x-action-menu-item>
  </x-action-menu>
</template>

<script>
  import xActionMenu from '../../neurons/data/ActionMenu.vue'
  import xActionMenuItem from '../../neurons/data/ActionMenuItem.vue'
  import xSelect from '../../axons/inputs/Select.vue'

  import { mapState, mapActions } from 'vuex'
  import { ADD_DATA_LABELS, LINK_DATA, UNLINK_DATA, ENFORCE_DATA } from '../../../store/actions'
  import { FETCH_DATA_CONTENT } from '../../../store/actions'

  export default {
    name: 'XEntitiesActionMenu',
    components: { xActionMenu, xActionMenuItem, xSelect },
    props: {
      module: {
        type: String,
        required: true
      },
      entities: {
        type: Object,
        default: () => {}
      },
      entitiesMeta: {
        type: Object,
        default: () => {}
      }
    },
    computed: {
      ...mapState({
        dataCount (state) {
          return state[this.module].count.data
        },
        enforcementOptions (state) {
          return state.enforcements.content.data.map(enforcement => {
            return {
              name: enforcement.name, title: enforcement.name
            }
          })
        },
        enforcementRestricted(state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Enforcements === 'Restricted'
        }
      }),
      selectionCount () {
        if (this.entities.include === undefined || this.entities.include) {
          return this.entities.ids.length
        }
        return this.dataCount - this.entities.ids.length
      }
    },
    data() {
      return {
        selectedEnforcement: ''
      }
    },
    mounted() {
      if (!this.enforcementRestricted && !this.enforcementOptions.length) {
        this.fetchContent({
          module: 'enforcements'
        })
      }
    },
    methods: {
      ...mapActions(
        {
          addLabels: ADD_DATA_LABELS,
          linkData: LINK_DATA,
          unlinkData: UNLINK_DATA,
          enforceData: ENFORCE_DATA,
          fetchContent: FETCH_DATA_CONTENT
        }),
      linkEntities () {
        return this.linkData({
          module: this.module, data: this.entities
        }).then(() => this.$emit('done'))
      },
      unlinkEntities () {
        return this.unlinkData({
          module: this.module, data: this.entities
        }).then(() => this.$emit('done'))
      },
      enforceEntities () {
        return this.enforceData({
          module: this.module, data: {
            entities: this.entities, enforcement: this.selectedEnforcement
          }
        })
      }
    }
  }
</script>

<style lang="scss">
  .x-form.expand .item {
    width: 100%;

    .object {
      width: 100%;
    }
  }
</style>