<template>
  <div class="x-entity-view">
    <div
      v-if="loading"
      class="v-spinner-bg"
    />
    <pulse-loader
      :loading="loading"
      color="#FF7D46"
    />
    <x-tabs
      v-show="!loading"
    >
      <x-tab
        v-if="!this.singleAdapter"
        id="specific"
        key="specific"
        title="Adapters Data"
        :selected="true"
      >
        <x-entity-adapters
          v-if="entityContent.adapters"
          :entity-id="entityId"
          :module="module"
          :adapters="entityContent.adapters"
        />
      </x-tab>
      <x-tab
        id="generic"
        key="generic"
        title="General Data"
        :selected="singleAdapter"
      >
        <x-entity-general
          :module="module"
          :entity-id="entityId"
          :basic="entityContent.basic"
          :advanced="entityContent.advanced"
        />
      </x-tab>
      <x-tab
        v-if="entityExtended.length"
        id="extended"
        key="extended"
        title="Extended Data"
      >
        <x-tabs :vertical="true">
          <x-tab
            v-for="(item, i) in entityExtended"
            :id="`data_${i}`"
            :key="`data_${i}`"
            :title="item.name"
            :selected="!i"
          >
            <x-custom :data="item.data" />
          </x-tab>
        </x-tabs>
      </x-tab>
      <x-tab
        v-if="entityTasks.length"
        id="ec_runs"
        key="tasks"
        title="Enforcement Tasks"
      >
        <x-entity-tasks :tasks="entityTasks" />
      </x-tab>
      <x-tab
        id="notes"
        key="notes"
        title="Notes"
      >
        <x-entity-notes
          :module="module"
          :entity-id="entityId"
          :notes="entityNotes"
          :read-only="readOnly || history !== null"
        />
      </x-tab>
      <x-tab
        id="tags"
        key="tags"
        title="Tags"
      >
        <x-entity-tags
          :module="module"
          :entity-id="entityId"
          :tags="entityLabels"
          :read-only="readOnly"
        />
      </x-tab>
    </x-tabs>
  </div>
</template>

<script>
  import xTabs from '../../../axons/tabs/Tabs.vue'
  import xTab from '../../../axons/tabs/Tab.vue'
  import xCustom from '../../../neurons/schema/Custom.vue'
  import xEntityAdapters from './Adapters.vue'
  import xEntityGeneral from './General.vue'
  import xEntityNotes from './Notes.vue'
  import xEntityTasks from './Tasks.vue'
  import xEntityTags from './Tags.vue'
  import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

  import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
  import { SINGLE_ADAPTER } from '../../../../store/getters'
  import {SELECT_DATA_CURRENT} from '../../../../store/mutations'
  import { FETCH_DATA_CURRENT, FETCH_DATA_HYPERLINKS, FETCH_DATA_CURRENT_TASKS } from '../../../../store/actions'

  export default {
    name: 'XEntityLayout',
    components: {
      xTabs, xTab, xCustom, PulseLoader,
      xEntityAdapters, xEntityGeneral, xEntityNotes, xEntityTasks, xEntityTags
    },
    props: {
      module: {
        type: String,
        required: true
      },
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    computed: {
      ...mapState({
        entity (state) {
          return state[this.module].current
        },
        fields (state) {
          return state[this.module].fields.data
        },
        fetchingData (state) {
          return state[this.module].current.fetching
        }
      }),
      ...mapGetters({
        singleAdapter: SINGLE_ADAPTER
      }),
      entityId () {
        return this.$route.params.id
      },
      entityContent () {
        return this.entity.data
      },
      entityGenericData () {
        return this.entityContent.data || []
      },
      entityNotes () {
        let notes = this.entityGenericData.find(item => item.name === 'Notes')
        return notes ? notes.data : []
      },
      entityExtended() {
        return this.entityGenericData.filter(item => item.name !== 'Notes')
      },
      entityLabels () {
        return this.entityContent.labels || []
      },
      entityTasks () {
        return this.entity.tasks.data
      },
      history () {
        if (this.$route.query.history === undefined) return null
        return this.$route.query.history
      },
      loading () {
        return this.fetchingData || !this.fields || !this.fields.generic || !this.fields.schema
                || !this.entityContent || this.entity.id !== this.entityId
                || (this.historyDate && this.entityDate !== this.historyDate)
      },
      entityDate () {
        if (!this.entityContent.updated) return null
        return new Date(this.entityContent.updated).toISOString().substring(0, 10)
      },
      historyDate () {
        if (!this.history) return null
        return this.history.substring(0, 10)
      }
    },
    created () {
      this.fetchDataHyperlinks({ module: this.module })
      if (this.entity.id !== this.entityId) {
        this.fetchDataCurrent({
          module: this.module,
          id: this.entityId,
          history: this.history
        })
      }
    },
    mounted() {
      this.fetchDataCurrentTasks({
        module: this.module,
        id: this.entityId,
        history: this.history
      })
    },
    beforeDestroy() {
      this.selectCurrentEntity({
        module: this.module, id: ''
      })
    },
    methods: {
      ...mapMutations({
        selectCurrentEntity: SELECT_DATA_CURRENT,
      }),
      ...mapActions({
         fetchDataCurrent: FETCH_DATA_CURRENT,
         fetchDataHyperlinks: FETCH_DATA_HYPERLINKS,
         fetchDataCurrentTasks: FETCH_DATA_CURRENT_TASKS
       })
    }
  }
</script>

<style lang="scss">
    .x-entity-view {
        position: relative;
        height: 100%;

        .x-tabs {
            width: 100%;
            height: 100%;

            .header {
                .x-title .text {
                    white-space: pre-wrap;
                }
            }

            .body {
                .content-header {
                    padding-bottom: 4px;
                    margin-bottom: 12px;
                    border-bottom: 2px solid rgba($theme-orange, 0.4);

                    .server-info {
                        text-transform: uppercase;
                    }
                }

                .x-list {
                    height: 100%;
                    overflow: auto;

                    > .x-array-view > .array {
                        display: grid;
                        grid-template-columns: 50% 50%;
                        grid-gap: 4px 0;

                        .object {
                            width: 100%;
                        }

                        .array {
                            margin-left: 20px;
                            .object {
                                width: calc(100% - 24px);
                            }
                        }
                        .numbered > .object > .x-array-view > .array {
                            margin-left: 0;
                        }
                    }
                }

                .specific .x-list {
                    height: calc(100% - 36px);
                    white-space: pre;

                    > .x-array-view > .array {
                        display: block;

                        > .item-container > .item > .object > .x-array-view > .array {
                            overflow-wrap: break-word;
                            display: grid;
                            grid-template-columns: 50% 50%;
                            grid-gap: 12px 24px;
                            margin-left: 0;

                            .separator {
                                grid-column-end: span 2;
                            }
                        }
                    }
                }
            }

            .tag-edit .x-button {
                text-align: right;
            }
        }
    }
</style>
