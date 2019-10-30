<template>
  <x-page title="adapters" class="x-adapters">
    <div class="adapters-search">
      <x-search-input class="adapters-search_input" v-model="searchText" placeholder="Search Adapters..." />
      <md-switch
        v-model="showOnlyConfigured"
        class="md-primary"
        >Configured Only ({{configuredAdaptersCount}})</md-switch>
    </div>
    <div class="adapters-table">
      <table class="table">
        <thead>
          <tr class="table-row">
            <th class="status">&nbsp;</th>
            <th class="row-data">Name</th>
            <th class="row-data">Description</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredData" @click="configAdapter(item['id'])" class="table-row" :key="item.id">
            <td class="status">
              <div class="symbol">
                  <div v-if="item.successClients" class="status_success">
                    <svg-icon class="status_icon" :name="`symbol/success`" :original="true" height="13px"></svg-icon>
                    <p class="status_clients-count">{{item.successClients}}</p>
                  </div>
                  <div  v-if="item.errorClients" class="status_error">
                    <svg-icon class="status_icon" :name="`symbol/error`" :original="true" height="13px"></svg-icon>
                    <p class="status_clients-count">{{item.errorClients}}</p>
                  </div>
              </div>
              <div class="marker" :class="`indicator-bg-${item['status'] || 'void'}`"></div>
            </td>
            <td class="row-data title" :id="item.id">
              <x-title class="adapter-title" :id="item.id" :logo="`adapters/${item.id}`">{{ item.title }}</x-title>
            </td>
            <td class="row-data description">
              <div class="content">{{ item.description }}</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </x-page>
</template>


<script>
    import xPage from '../axons/layout/Page.vue'
    import xTitle from '../axons/layout/Title.vue'
    import xSearchInput from '../neurons/inputs/SearchInput.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {FETCH_ADAPTERS} from '../../store/modules/adapters'
    import { CONNECT_ADAPTERS } from '../../constants/getting-started'
    import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../store/modules/onboarding';

    function getConfiguredAdapters(adapter) {
        // configured adapter is one that has at least 1 client configured
        return adapter.clients.length
    }

    function getConnectedAdapters(adapter) {
        return adapter.successClients
    }

    export default {
        name: 'x-adapters',
        components: {xPage, xTitle, xSearchInput},
        computed: {
            ...mapState({
                adaptersData(state) {
                    return state.adapters.adapters.data
                }
            }),
            filteredData() {
                const searchTerm = this.searchText.toLowerCase()
                let res = this.adaptersData
                if (this.searchText) {
                    res = res.filter(a => a.title.toLowerCase().includes(searchTerm))
                }
                if (this.showOnlyConfigured) {
                    res = res.filter(getConfiguredAdapters)
                }
                return res
            },
            configuredAdaptersCount() {
                return this.filteredData.filter(getConfiguredAdapters).length
            },
        },
        data() {
            return {
                searchText: '',
                showOnlyConfigured: false,
            }
        },
        methods: {
            ...mapActions({fetchAdapters: FETCH_ADAPTERS, milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION}),
            configAdapter(adapterId) {
                /*
                    Fetch adapters requested to be configured asynchronously, before navigating to the
                    configuration page, so it will return meanwhile
                 */
                this.$router.push({path: `adapters/${adapterId}`})
            },
            notifyIfMilestoneCompleted() {
                if (this.filteredData.filter(getConnectedAdapters).length >= 3) {
                    this.milestoneCompleted({ milestoneName: CONNECT_ADAPTERS})
                }
            }
        },
        watch: {
            configuredAdaptersCount: function (value) {
                this.notifyIfMilestoneCompleted()
            }
        },
        created() {
            this.fetchAdapters()
        },
        mounted() {
            this.notifyIfMilestoneCompleted()
        }
    }
</script>


<style lang="scss">
    .x-adapters {
        .adapters-search {
            margin-bottom: 12px;
            display: flex;
            justify-content: center;

            &_input{
                width: 50%;
                margin-right: 10px;
            }

            .md-primary {
                margin: 0;
                width: 20%;
                padding: 5px 0;
            }
        }

        .adapters-table {
            height: calc(100% - 42px);
            overflow: auto;

            .table {
                border-collapse: separate;
                border-spacing: 0 8px;
                font-size: 14px;
                overflow: hidden;

                .table-row {
                    .row-data {

                        &.title {
                            width: 20%;

                            .adapter-title {
                                .text {
                                    white-space: unset;
                                    overflow: unset;
                                    text-overflow: unset;
                                    word-wrap: break-word;
                                }
                            }
                        }

                        &.description {
                            width: 80%
                        }
                        background: $theme-white;
                        vertical-align: middle;
                        padding: 12px;
                        position: relative;

                        &:last-child {
                            border-bottom-right-radius: 4px;
                            border-top-right-radius: 4px;
                        }

                        .content {
                            line-height: 1.2em;
                            overflow: hidden;
                            display: -webkit-box;
                            -webkit-line-clamp: 3;
                            -webkit-box-orient: vertical;
                        }
                    }

                    .status {
                        display: flex;
                        box-shadow: none;

                        .symbol {
                                flex: 1 0 auto;
                                text-align: center;
                                line-height: calc(3.6em + 24px);
                                margin: 0 12px;
                                display: flex;
                                flex-direction: column;
                                justify-content: center;
                             & > div {
                                 display: flex;
                                flex-direction: column;
                                justify-content: space-around;
                             }
                            .status {
                                &_clients-count {
                                    margin: 0;
                                    padding: 2px 0;
                                    line-height: 12px;
                                    font-size: 12px;
                                    font-weight: 600;
                                }

                                &_icon {
                                    margin: 2px 0;
                                }

                            }
                            
                        }

                        .marker {
                            width: 10px;
                            height: calc(4px + 3.6em + 24px);
                            margin: -2px -8px;
                            border-bottom-left-radius: 4px;
                            border-top-left-radius: 4px;

                        }
                    }
                }

                thead {
                    overflow: auto;
                    .table-row .row-data:nth-child(2) {
                        border-bottom-left-radius: 4px;
                        border-top-left-radius: 4px;
                    }
                }

                tbody {
                    overflow: auto;
                    .table-row:hover {
                        cursor: pointer;
                        transform: scale(1.02);
                    }
                }
            }

        }
    }
</style>