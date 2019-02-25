<template>
  <x-action-menu
    :module="module"
    :entities="entities"
    @done="$emit('done')"
  >
    <template v-if="module === 'devices'">
      <x-action-menu-item
        :handle-save="saveBlacklist"
        message="Blacklist saved"
        title="Blacklist..."
        action-text="Blacklist"
      >
        <div>Add {{ selectionCount }} devices to Blacklist?</div>
        <div>These devices will be prevented from executing code on.</div>
      </x-action-menu-item>
    </template>
    <x-action-menu-item
      :title="`Link ${module}...`"
      :handle-save="linkEntities"
      :message="`${module} were linked`"
      action-text="Save"
      :disabled="selectionCount > 10"
    >
      <div
        v-if="selectionCount > 10"
        class="error"
      >
        Maximal amount of {{ module }} to link is 10
      </div>
      <div
        v-else
        class="warn-delete"
      >
        You are about to link {{ selectionCount }} {{ module }}.
      </div>
    </x-action-menu-item>
    <x-action-menu-item
      :title="`Unlink ${module}...`"
      :handle-save="unlinkEntities"
      :message="`${module} were unlinked`"
      action-text="Save"
    >
      <div class="warn-delete">
        You are about to unlink {{ selectionCount }} {{ module }}.
        This means that each of the adapter {{ module }} inside
        will become a standalone axonius entity.
      </div>
    </x-action-menu-item>
  </x-action-menu>
</template>

<script>
    import xActionMenu from '../../neurons/data/ActionMenu.vue'
    import xActionMenuItem from '../../neurons/data/ActionMenuItem.vue'

    import {mapState, mapActions} from 'vuex'
    import {ADD_DATA_LABELS, LINK_DATA, UNLINK_DATA} from '../../../store/actions'

    export default {
        name: 'XEntitiesActionMenu',
        components: {xActionMenu, xActionMenuItem},
        props: {
            module: {
                type: String,
                required: true
            },
            entities: {
                type: Object,
                default: () => {}
            }},
        computed: {
            ...mapState({
                dataCount(state) {
                    return state[this.module].count.data
                }
            }),
            selectionCount() {
                if (this.entities.include === undefined || this.entities.include) {
                    return this.entities.ids.length
                }
                return this.dataCount - this.entities.ids.length
            }
        },
        methods: {
            ...mapActions(
                {
                    addLabels: ADD_DATA_LABELS,
                    linkData: LINK_DATA,
                    unlinkData: UNLINK_DATA
                }),
            saveBlacklist() {
                /*
                Blacklist is currently implemented by checking for a designated tag,
                Therefore, adding this tag to selected devices
                 */
                return this.addLabels({
                    module: 'devices', data: {
                        entities: this.entities, labels: ['do_not_execute']
                    }
                })
            },
            linkEntities() {
                return this.linkData({
                    module: this.module, data: this.entities
                }).then(() => this.$emit('done'))
            },
            unlinkEntities() {
                return this.unlinkData({
                    module: this.module, data: this.entities
                }).then(() => this.$emit('done'))
            },
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