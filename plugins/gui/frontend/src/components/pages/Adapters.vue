<template>
  <x-page
    title="adapters"
    class="x-adapters"
  >
    <div class="adapters-search">
      <x-search-input
        v-model="searchText"
        class="adapters-search_input"
        placeholder="Search Adapters..."
      />
      <md-switch
        v-model="showOnlyConfigured"
        class="md-primary"
      >Configured Only ({{ configuredAdaptersCount }})</md-switch>
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
          <tr
            v-for="item in filteredData"
            :key="item.id"
            class="table-row"
            @click="configAdapter(item['id'])"
          >
            <td class="status">
              <div class="summary">
                <div v-if="item.successClients">
                  <md-icon
                    md-src="/src/assets/icons/symbol/success.svg"
                    class="icon-success"
                  />
                  <p class="summary_count">{{ item.successClients }}</p>
                </div>
                <div  v-if="item.errorClients">
                  <md-icon
                    md-src="/src/assets/icons/symbol/error.svg"
                    class="icon-error"
                  />
                  <p class="summary_count">{{ item.errorClients }}</p>
                </div>
              </div>
              <div
                class="marker"
                :class="`indicator-bg-${item['status'] || 'void'}`"
              />
            </td>
            <td
              :id="item.id"
              class="row-data row-title"
            >
              <x-title
                :id="item.id"
                class="adapter-title"
                :logo="`adapters/${item.id}`"
              >{{ item.title }}</x-title>
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
        name: 'XAdapters',
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
            successfullyconfiguredAdapters() {
              return this.adaptersData.filter(getConnectedAdapters).length
            }
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
            successfullyconfiguredAdapters: function (value) {
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

      &_input {
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

            &.row-title {
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

            .summary {
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
              .md-icon {
                min-width: 16px;
                width: 16px;
              }
              &_count {
                margin: 0;
                padding: 2px 0;
                line-height: 12px;
                font-size: 12px;
                font-weight: 600;
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