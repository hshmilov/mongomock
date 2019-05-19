<template>
  <div>
    <div class="x-data">
      <x-table-data
        :schema="schema"
        :data="data"
        :sort="sort"
        ref="data"
      />
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
          :class="{ top, left }"
          @click.stop=""
        >
          <transition name="horizontal-fade">
            <div
              v-if="expandData"
              class="content"
            >
              <x-table v-bind="detailsTable" />
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
            class="item"
          />
        </div>
      </transition>
    </div>
  </div>
</template>

<script>
  import xTable from '../../axons/tables/Table.vue'
  import xTableData from '../../axons/tables/TableData.vue'

  import {mapState} from 'vuex'

  export default {
    name: 'XEntityTableData',
    components: {
      xTable,
      xTableData
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
      hoverRow: {
        type: Boolean,
        default: false
      },
      expandRow: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        expandData: false,
        calcPosition: false
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
      adaptersList () {
        return [...this.data[this.adaptersFieldName]].sort().map(adapter => [adapter])
      },
      adaptersLength () {
        return this.adaptersList.length
      },
      details () {
        if (this.fieldName === this.adaptersFieldName) {
          return this.adaptersList
        }
        return this.data[`${this.fieldName}_details`]
      },
      showExpand () {
        return (this.hoverRow || this.expandData) && this.adaptersLength > 1 && this.fieldName.includes('specific_data')
                && Boolean(this.$refs.data && this.$refs.data.$el.textContent.trim())
      },
      detailsTable () {
        let baseTable = {
          fields: [
            this.adaptersSchema,
            this.schema
          ],
          data: this.details.map((detail, i) => {
            return {
              [this.adaptersFieldName]: [this.adaptersList[i]],
              [this.fieldName]: detail
            }
          })
        }
        if (this.schema.type === 'string' && this.schema.format === 'date-time') {
          baseTable.fields.push({
            name: 'days', title: 'Days', type: 'integer'
          })
          baseTable.data = baseTable.data.map(item => {
            if (!item[this.schema.name]) return item
            return {...item,
              days: Math.ceil((new Date() - new Date(item[this.schema.name])) / 60 / 60 / 24 / 1000)
            }
          }).sort((a, b) => a.days - b.days)
        }
        return baseTable
      },
      top () {
        if (!this.calcPosition || !this.$refs.popup) return false
        return (this.$refs.popup.getBoundingClientRect().bottom > window.innerHeight - 80)
      },
      left () {
        if (!this.calcPosition || !this.$refs.popup) return false
        return (this.$refs.popup.getBoundingClientRect().right > window.innerWidth - 24)
      }
    },
    methods: {
      toggleCell () {
        this.expandData = !this.expandData
      }
    },
    updated() {
      if (this.expandData) {
        this.calcPosition = true
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
                    display: grid;
                    grid-template-columns: 1fr 2fr;
                    max-height: 30vh;
                    overflow: auto;
                  
                    .x-table {
                      width: min-content;
                      height: auto;
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
    }


    .details-list-container {
        overflow: hidden;
        margin: 0px -8px;

        .list {
            margin-top: 8px;
            display: grid;
            background-color: rgba($grey-2, 0.6);

            .item {
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