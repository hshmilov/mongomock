<template>
  <div class="x-query-state">
    <div class="header">
      <div class="title">{{ enforcement? enforcement.message: title }}</div>
      <div class="status">{{ status }}</div>
    </div>
    <x-button
      v-if="enforcement"
      link
      @click="navigateFilteredTask"
    >Go to Task</x-button>
    <x-button
      v-else-if="!selectedView || !isEdited"
      id="query_save"
      link
      :disabled="disabled"
      @click="openSaveView"
    >Save as</x-button>
    <x-dropdown v-else>
      <x-button
        slot="trigger"
        link
        :disabled="disabled"
        @click.stop="saveSelectedView"
      >Save</x-button>
      <div slot="content">
        <x-button
          link
          @click="openSaveView"
        >Save as</x-button>
        <x-button
        link
        @click="reloadSelectedView"
        >Discard Changes</x-button>
      </div>
    </x-dropdown>
    <x-button
      link
      @click="resetQuery"
    >Reset</x-button>
    <x-historical-date
      v-model="historical"
      :module="module"
    />
    <x-modal
      v-show="saveModal.isActive"
      approve-text="Save"
      approve-id="query_save_confirm"
      size="md"
      @close="closeSaveView"
      @confirm="confirmSaveView"
      @enter="$emit('tour', 'querySaveConfirm')"
      @leave="$emit('tour', 'queryList')"
    >
      <div
        slot="body"
        class="query-save"
      >
        <label for="saveName">Save as:</label>
        <input
          id="saveName"
          v-model="saveModal.name"
          class="flex-expand"
          @keyup.enter="confirmSaveView"
        >
      </div>
    </x-modal>
  </div>
</template>

<script>
  import xButton from '../../../axons/inputs/Button.vue'
  import xDropdown from '../../../axons/popover/Dropdown.vue'
  import xHistoricalDate from '../../../neurons/inputs/HistoricalDate.vue'
  import xModal from '../../../axons/popover/Modal.vue'
  import {defaultFields} from '../../../../constants/entities'

  import {mapState, mapMutations, mapActions} from 'vuex'
  import {UPDATE_DATA_VIEW} from '../../../../store/mutations'
  import {SAVE_DATA_VIEW} from '../../../../store/actions'

  export default {
    name: 'XQueryState',
    components: {
      xButton, xDropdown, xHistoricalDate, xModal
    },
    props: {
      module: {
        type: String,
        required: true
      },
      disabled: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        saveModal: {
          isActive: false,
          name: ''
        }
      }
    },
    computed: {
      ...mapState({
        view (state) {
          return state[this.module].view
        },
        allowedDates (state) {
          return state.constants.allowedDates[this.module]
        },
        selectedView (state) {
          let uuid = state[this.module].selectedView
          if (!uuid) return null
          return state[this.module].views.saved.content.data.find(view => view.uuid === uuid)
        }
      }),
      enforcement () {
        return this.view.enforcement
      },
      historical: {
        get () {
          if (!this.view.historical) return ''
          return this.view.historical.substring(0, 10)
        },
        set (newDate) {
          this.updateView({
            module: this.module, view: {
              historical: this.allowedDates[newDate]
            }
          })
        }
      },
      title () {
        if (this.selectedView) {
          return this.selectedView.name
        }
        return 'New Query'
      },
      isEdited () {
        if (!this.selectedView || !this.selectedView.view) return false
        return ((this.selectedView.view.query.filter !== this.view.query.filter)
                || !this.arraysEqual(this.view.fields, this.selectedView.view.fields)
                || this.view.sort.field !== this.selectedView.view.sort.field)
      },
      status () {
        if (this.enforcement) return ''
        return !this.selectedView? '[Unsaved]' : (this.isEdited ? '[Edited]' : '')
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      ...mapActions({
        saveView: SAVE_DATA_VIEW
      }),
      resetQuery () {
        this.updateView({
          module: this.module, view: {
            enforcement: null,
            query: {
              filter: '', expressions: [], search: ''
            },
            sort: {
              field: '', desc: true
            },
            fields: defaultFields[this.module]
          },
          uuid: null
        })
      },
      navigateFilteredTask() {
        this.$router.push({path: `/enforcements/tasks/${this.enforcement.id}`})
      },
      openSaveView () {
        this.saveModal.isActive = true
      },
      closeSaveView () {
        this.saveModal.isActive = false
      },
      confirmSaveView () {
        if (!this.saveModal.name) return

        this.saveView({
          module: this.module,
          name: this.saveModal.name
        }).then(() => this.saveModal.isActive = false)
      },
      saveSelectedView () {
        if (!this.selectedView) return

        this.saveView({
          module: this.module,
          name: this.selectedView.name
        })
      },
      reloadSelectedView () {
        this.updateView({
          module: this.module,
          view: { ...this.selectedView.view }
        })
      },
      arraysEqual (arrA, arrB) {
        return !arrA.filter(x => !arrB.includes(x)).length || arrB.filter(x => !arrA.includes(x)).length
      }
    }
  }
</script>

<style lang="scss">
    .x-query-state {
        display: flex;
        width: 100%;
        align-items: center;
        .header {
            display: flex;
            line-height: 28px;
            margin-bottom: 8px;
            .title {
                font-size: 16px;
                font-weight: 400;
                margin-right: 8px;
            }
            .status {
                color: $grey-3;
            }
        }
        .x-button {
            margin-bottom: 8px;
        }
        .x-dropdown {
          .trigger {
            padding-right: 12px;
            &:after {
              margin-top: -6px;
            }
          }
          .content {
            &.expand {
              min-width: max-content;
            }
            .x-button {
              display: block;
            }
          }
        }
    }
</style>