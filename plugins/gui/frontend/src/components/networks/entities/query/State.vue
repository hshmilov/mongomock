<template>
  <div class="x-query-state">
    <div class="header">
      <template v-if="enforcement">
        <div class="title">{{ enforcement.name }} - Task {{ enforcement.task }}</div>
        <div class="subtitle">{{ enforcement.outcome }} results of "{{ enforcement.action }}" action</div>
      </template>
      <x-button
        v-else-if="selectedView && !readOnly"
        link
        class="title"
        @click="openRenameView"
      >{{ selectedView.name }}</x-button>
      <div
        v-else-if="selectedView"
        class="title"
      >{{ selectedView.name }}</div>
      <div
        v-else
        class="title"
      >New Query</div>
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
          :disabled="disabled"
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
    <x-save-modal
      v-if="viewNameModal.isActive"
      :module="module"
      :view="viewNameModal.view"
      @close="closeSaveView"
      @enter="$emit('tour', 'querySaveConfirm')"
    />
  </div>
</template>

<script>
  import xButton from '../../../axons/inputs/Button.vue'
  import xDropdown from '../../../axons/popover/Dropdown.vue'
  import xHistoricalDate from '../../../neurons/inputs/HistoricalDate.vue'
  import xSaveModal from './SaveModal.vue'
  import {defaultFields} from '../../../../constants/entities'

  import {mapState, mapMutations, mapActions} from 'vuex'
  import {UPDATE_DATA_VIEW} from '../../../../store/mutations'
  import { SAVE_DATA_VIEW } from '../../../../store/actions'

  export default {
    name: 'XQueryState',
    components: {
      xButton, xDropdown, xHistoricalDate, xSaveModal
    },
    props: {
      module: {
        type: String,
        required: true
      },
      readOnly: {
        type: Boolean,
        default: false
      },
      valid: {
        type: Boolean,
        default: true
      }
    },
    data () {
      return {
        viewNameModal: {
          isActive: false,
          view: null
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
      disabled () {
        return !this.valid || this.readOnly || this.isDefaultView
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
          this.$emit('done')
        }
      },
      title () {
        if (this.enforcement) {
          return ``
        }
        if (this.selectedView) {
          return this.selectedView.name
        }
        return 'New Query'
      },
      isDefaultView () {
        return this.view.query.filter === ''
                && this.arraysEqual(this.view.fields, defaultFields[this.module])
                && this.view.sort.field === ''
                && (!Object.keys(this.view.colFilters).length || !Object.values(this.view.colFilters).find(val => val))
      },
      isEdited () {
        return this.selectedView && this.selectedView.view &&
                (this.selectedView.view.query.filter !== this.view.query.filter
                || !this.arraysEqual(this.view.fields, this.selectedView.view.fields)
                || this.view.sort.field !== this.selectedView.view.sort.field
                || this.view.sort.desc !== this.selectedView.view.sort.desc
                || !this.objsEqual(this.view.colFilters, this.selectedView.view.colFilters))
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
            fields: defaultFields[this.module],
            colFilters: {}
          },
          uuid: null
        })
        this.$emit('done')
      },
      navigateFilteredTask() {
        this.$router.push({path: `/tasks/${this.enforcement.id}`})
      },
      openSaveView () {
        this.viewNameModal.isActive = true
      },
      closeSaveView () {
        this.viewNameModal.isActive = false
        this.$emit('tour', 'queryList')
      },
      openRenameView () {
        this.viewNameModal.isActive = true
        this.viewNameModal.view = {
          uuid: this.selectedView.uuid,
          name: this.selectedView.name
        }
      },
      saveSelectedView () {
        if (!this.selectedView || !this.selectedView.uuid) return

        this.saveView({
          module: this.module,
          name: this.selectedView.name,
          uuid: this.selectedView.uuid
        })
      },
      reloadSelectedView () {
        this.updateView({
          module: this.module,
          view: { ...this.selectedView.view }
        })
        this.$emit('done')
      },
      arraysEqual (arrA, arrB) {
        return !arrA.filter(x => !arrB.includes(x)).length && !arrB.filter(x => !arrA.includes(x)).length
      },
      objsEqual (objA, objB) {
        if (!objA || !objB) {
          return true
        }
        return this.arraysEqual(Object.keys(objA), Object.keys(objB))
                && this.arraysEqual(Object.values(objA), Object.values(objB))
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
            margin-right: 16px;
            .title {
                font-size: 16px;
                font-weight: 400;
                color: $theme-black;
                margin-right: 8px;
                &.x-button {
                  padding: 0;
                  margin-bottom: 0;
                }
            }
            .subtitle {
              font-size: 14px;
            }
            .status {
                color: $grey-3;
            }
        }
        .x-button {
            margin-bottom: 8px;
            padding: 4px;
            margin-right: 16px;
        }
        .x-dropdown {
          margin-right: 16px;
          .trigger {
            padding-right: 8px;
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