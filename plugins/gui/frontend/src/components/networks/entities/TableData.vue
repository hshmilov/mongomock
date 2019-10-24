<template>
  <div>
    <div
      class="x-data"
      @mouseover="onHoverData"
      @mouseleave="onLeaveData"
    >
      <x-table-data
        :schema="schema"
        :data="data"
        :sort="sort"
        :filter="filter"
        ref="data"
      />
      <div class="data-table-container">
        <x-tooltip v-if="hoverData">
          <x-table
            slot="body"
            v-bind="adaptersDetailsTable"
          />
        </x-tooltip>
      </div>
      <div class="details-table-container">
        <md-icon
          v-if="showExpand"
          class="trigger"
          :class="{active: expandData}"
          @click.native.stop="toggleCell"
        >
          <template v-if="expandData">chevron_left</template>
          <template v-else>chevron_right</template>
        </md-icon>
        <div
          ref="popup"
          class="popup"
          :class="{ top: position.top, left: position.left }"
          @click.stop=""
        >
          <transition name="horizontal-fade">
            <div
              v-if="expandData"
              class="content"
            >
              <x-table v-bind="detailsTable">
                <x-table-data
                  slot-scope="props"
                  :module="module"
                  v-bind="props"
                />
              </x-table>
            </div>
          </transition>
        </div>
      </div>
    </div>
    <div class="details-list-container">
      <transition name="vertical-fade">
        <div
          v-if="expandRow"
          class="list"
        >
          <x-table-data
            v-for="(detail, index) in details"
            :key="index"
            :schema="schema"
            :data="detail"
            :sort="sort"
            :filter="filter"
            class="item"
          />
        </div>
      </transition>
    </div>
  </div>
</template>

<script>
  import xTable from '../../axons/tables/Table.vue'
  import xTableData from '../../neurons/data/TableData.vue'
  import xTooltip from '../../axons/popover/Tooltip.vue'
  import {pluginMeta} from '../../../constants/plugin_meta'

  import {mapState} from 'vuex'

  export default {
    name: 'XEntityTableData',
    components: {
      xTable,
      xTableData,
      xTooltip
    },
    props: {
      module: {
        type: String,
        required: true
      },
      schema: {
        type: Object,
        required: true
      },
      data: {
        type: Object,
        required: true
      },
      sort: {
        type: Object,
        default: () => {
          return {
            field: '', desc: true
          }
        }
      },
      filter: {
        type: String,
        default: ''
      },
      hoverRow: {
        type: Boolean,
        default: false
      },
      expandRow: {
        type: Boolean,
        default: false
      },
    },
    data () {
      return {
        hoverData: false,
        expandData: false,
        position: {
          top: false,
          left: false
        }
      }
    },
    computed: {
      ...mapState({
        adaptersSchema(state) {
          return state[this.module].fields.data.generic[0]
        }
      }),
      fieldName () {
        return this.schema.name
      },
      adaptersFieldName () {
        return this.adaptersSchema.name
      },
      isAdaptersField () {
        return this.fieldName === this.adaptersFieldName
      },
      adaptersLength () {
        return this.data[this.adaptersFieldName].length
      },
      showExpand () {
        return (this.hoverRow || this.expandData) && this.adaptersLength > 1 && this.fieldName.includes('specific_data')
                && Boolean(this.$refs.data && this.$refs.data.$el.textContent.trim())
      },
      adaptersListSorted() {
        return this.data[this.adaptersFieldName].concat().sort().map(adapter => [adapter])
      },
      details () {
        if (this.isAdaptersField) {
          return this.adaptersListSorted
        }
        return this.data[`${this.fieldName}_details`]
      },
      detailsTable () {
        let baseTable = {
          fields: [
            this.adaptersSchema,
            this.schema
          ],
          data: this.details.map((detail, i) => {
            return {
              [this.adaptersFieldName]: this.adaptersListSorted[i],
              [this.fieldName]: detail
            }
          }),
          colFilters: {
            [this.schema.name]: this.filter
          },
          filterable: false
        }
        if (this.schema.type === 'string' && this.schema.format === 'date-time') {
          baseTable.fields.push({
            name: 'days', title: 'Days', type: 'integer'
          })
          baseTable.data = baseTable.data.map(item => {
            if (!item[this.schema.name]) return item
            let nowDate = new Date()
            nowDate.setHours(0, 0, 0, 0)
            let itemDate = new Date(item[this.schema.name])
            itemDate.setHours(0, 0, 0, 0)
            return {...item,
              days: Math.ceil((nowDate.getTime() - itemDate.getTime()) / 60 / 60 / 24 / 1000)
            }
          }).sort((a, b) => {
            if (a.days === undefined) return 1
            if (b.days === undefined) return -1
            return a.days - b.days
          })
        }
        return baseTable
      },
      adaptersDetailsTable () {
        return {
          fields: [
            this.schema, {
              name: 'name', title: 'Name', type: 'string'
          }],
          data: this.adaptersListSorted.map(adapter => {
            return {
              [this.fieldName]: adapter,
              name: pluginMeta[adapter[0]] ? pluginMeta[adapter[0]].title : adapter[0]
            }
          }),
          colFilters: {
            [this.schema.name]: this.filter
          },
          filterable: false
        }
      }
    },
    methods: {
      toggleCell () {
        this.expandData = !this.expandData
        if (this.expandData) {
          this.$nextTick(() => {
            let boundingBox = this.$refs.popup.getBoundingClientRect()
            this.position = {
              top: this.position.top || Boolean(boundingBox.bottom > window.innerHeight - 80),
              left: this.position.left || Boolean(boundingBox.right > window.innerWidth - 24)
            }
          })
        }
      },
      onHoverData () {
        if (!this.isAdaptersField) {
          return
        }
        this.hoverData = true
      },
      onLeaveData () {
        this.hoverData = false
      }
    }
  }
</script>

<style lang="scss">
    .x-data {
        display: flex;

        .details-table-container {
            min-width: 24px;
            position: relative;

            .trigger {
                font-size: 16px !important;
                border: 1px solid $theme-black;
                border-radius: 100%;
                height: 14px;
                margin-left: 4px;
                transition: all .4s cubic-bezier(.4,0,.2,1);
                &:hover, &.active {
                    border-color: $theme-orange;
                }
            }

            .popup {
                overflow: visible;
                position: absolute;
                width: min-content;
                z-index: 200;
                cursor: default;

                &.top {
                    bottom: 100%;
                }
                &.left {
                    right: 0;
                }

                .content {
                    background-color: $theme-white;
                    box-shadow: $popup-shadow;
                    padding: 4px;
                    border-radius: 4px;
                    max-height: 30vh;
                    .x-table {
                      width: min-content;
                      max-height: calc(30vh - 8px);
                    }
                }

                .horizontal-fade-enter-active {
                    transition: all .4s cubic-bezier(1.0, 0.4, 0.8, 1.0);
                }

                .horizontal-fade-leave-active {
                    transition: all .2s ease;
                }

                .horizontal-fade-enter, .horizontal-fade-leave-to {
                    transform: translateX(-100%);
                    opacity: 0;
                }
            }
        }

        .data-table-container {
          position: relative;
        }
    }

    .details-list-container {
        overflow: visible;
        margin: 0px -8px;

        .list {
            margin-top: 2px;
            display: grid;
            background-color: rgba($grey-2, 0.6);

            > .item {
                height: 30px;
                display: flex;
                align-items: center;
                border-bottom: 2px solid $theme-white;
                padding: 4px 8px;

                &:last-child {
                    border: none;
                }
            }
        }

        .vertical-fade-enter-active {
            transition: all .4s cubic-bezier(1.0, 0.4, 0.8, 1.0);
        }

        .vertical-fade-leave-active {
            transition: all .2s ease;
        }

        .vertical-fade-enter, .vertical-fade-leave-to {
            transform: translateY(-50%);
            opacity: 0;
        }
    }
</style>