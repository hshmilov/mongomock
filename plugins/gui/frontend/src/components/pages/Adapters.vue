<template>
  <XPage
    title="adapters"
    class="x-adapters"
  >
    <div class="adapters-search">
      <XSearchInput
        v-model="searchText"
        class="adapters-search_input"
        placeholder="Search Adapters..."
      />
      <div class="adapters-search-switch">
        <ASwitch
          v-model="showOnlyConfigured"
        />
        <span class="x-switch-label">{{ configuredSwitchLabel }}</span>
      </div>
    </div>
    <div
      v-if="!adaptersData.length && adaptersFetching"
      class="adapters-loader"
    >
      <PulseLoader
        color="#FF7D46"
        loading
      />
    </div>
    <div
      v-else
      class="adapters-table"
    >
      <table class="table">
        <thead>
          <tr class="table-row">
            <th class="status">
              &nbsp;
            </th>
            <th class="row-data">
              Name
            </th>
            <th class="row-data">
              Connection Status
            </th>
            <th class="row-data">
              Description
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in filteredData"
            :key="item.id"
            class="table-row"
            @click="configAdapter(item['id'])"
          >
            <td class="status-column">
              <div
                class="marker"
                :class="`indicator-bg-${item['status'] || 'void'}`"
              />
            </td>
            <td
              :id="item.id"
              class="row-data row-title"
            >
              <XTitle
                :id="item.id"
                class="adapter-title"
                :logo="`adapters/${item.id}`"
              >{{ item.title }}</XTitle>
            </td>
            <td class="row-data status">
              <div class="summary">
                <div
                  v-if="item.successClients"
                  class="summary_row"
                >
                  <XIcon
                    type="check-circle"
                    theme="filled"
                    class="icon-success"
                  />
                  <span class="summary_count">
                    {{ item.successClients }}
                  </span>
                </div>
                <div
                  v-if="item.errorClients"
                  class="summary_row"
                >
                  <XIcon
                    type="close-circle"
                    theme="filled"
                    class="icon-error"
                  />
                  <span class="summary_count">
                    {{ item.errorClients }}
                  </span>
                </div>
                <div
                  v-if="item.inactiveClients"
                  class="summary_row"
                >
                  <XIcon
                    type="pause-circle"
                    theme="filled"
                    class="icon-inactive"
                  />
                  <span class="summary_count">
                    {{ item.inactiveClients }}
                  </span>
                </div>
              </div>
            </td>
            <td class="row-data description">
              <div class="content">
                {{ item.description }}
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </XPage>
</template>


<script>
import PulseLoader from 'vue-spinner/src/PulseLoader.vue';
import {
  mapState, mapMutations, mapActions, mapGetters,
} from 'vuex';
import XPage from '@axons/layout/Page.vue';
import XTitle from '@axons/layout/Title.vue';
import XSearchInput from '@neurons/inputs/SearchInput.vue';
import { Switch as ASwitch } from 'ant-design-vue';


import { FETCH_ADAPTERS } from '@store/modules/adapters';
import { CONNECT_ADAPTERS } from '@constants/getting-started';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '@store/modules/onboarding';

function getConnectedAdapters(adapter) {
  return adapter.successClients;
}

export default {
  name: 'XAdapters',
  components: {
    XPage, XTitle, XSearchInput, PulseLoader, ASwitch,
  },
  computed: {
    ...mapState({
      adaptersData(state) {
        return state.adapters.adapters.data;
      },
      adaptersFetching(state) {
        return state.adapters.adapters.fetching;
      },
      tableFilter(state) {
        return state.adapters.tableFilter;
      },
    }),
    ...mapGetters({
      getConfiguredAdapters: 'getConfiguredAdapters',
    }),
    filteredData() {
      const searchTerm = this.searchText.toLowerCase();
      let res = this.showOnlyConfigured ? this.getConfiguredAdapters : this.adaptersData;
      if (this.searchText) {
        res = res.filter((a) => a.title.toLowerCase().includes(searchTerm));
      }
      return res;
    },
    configuredAdaptersCount() {
      return this.getConfiguredAdapters.length;
    },
    successfullyconfiguredAdapters() {
      return this.adaptersData.filter(getConnectedAdapters).length;
    },
    searchText: {
      get() {
        return this.tableFilter.searchText;
      },
      set(searchText) {
        this.setAdaptersTableFilter({
          searchText,
        });
      },
    },
    showOnlyConfigured: {
      get() {
        return this.tableFilter.showOnlyConfigured;
      },
      set(showOnlyConfigured) {
        this.setAdaptersTableFilter({
          showOnlyConfigured,
        });
      },
    },
    configuredSwitchLabel() {
      return `Configured only (${this.configuredAdaptersCount})`;
    },
  },
  methods: {
    ...mapMutations({
      setAdaptersTableFilter: 'setAdaptersTableFilter',
    }),
    ...mapActions({
      fetchAdapters: FETCH_ADAPTERS,
      milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION,
    }),
    configAdapter(adapterId) {
      /*
        Fetch adapters requested to be configured asynchronously, before navigating to the
        configuration page, so it will return meanwhile
     */
      this.$router.push({ path: `adapters/${adapterId}` });
    },
    notifyIfMilestoneCompleted() {
      if (this.filteredData.filter(getConnectedAdapters).length >= 3) {
        this.milestoneCompleted({ milestoneName: CONNECT_ADAPTERS });
      }
    },
  },
  watch: {
    successfullyconfiguredAdapters() {
      this.notifyIfMilestoneCompleted();
    },
  },
  created() {
    this.fetchAdapters();
  },
  mounted() {
    this.notifyIfMilestoneCompleted();
  },
};
</script>


<style lang="scss">
  .x-adapters {
    .adapters-search {
      margin-bottom: 12px;
      display: flex;
      justify-content: center;
      align-items: center;

      &_input {
        width: 50%;
        margin-right: 10px;
      }

      .md-primary {
        margin: 0;
        width: 20%;
        padding: 5px 0;
      }

      .adapters-search-switch {
        @include x-switch;
      }
    }
    .adapters-loader {
      height: calc(100% - 42px);
      width: 100%;
      display: flex;
      align-content: center;
      justify-content: center;
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
              width: calc(80% - 150px);
              height: 76px;
            }

            &.status {
              width: 150px;
              padding: 0px 12px;
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

          .status-column {
            position: relative;
            min-width: 35px;
            padding: 0;
            box-shadow: none;

            .marker {
              position: absolute;
              top: 0;
              right: 0;
              bottom: 0;
              width: 10px;
              margin: 0;
              border-bottom-left-radius: 4px;
              border-top-left-radius: 4px;
            }
          }
          .summary {
            display: flex;
            flex-direction: column;
            justify-content: center;
            font-size: 16px;
            padding: 5px;

            &_row {
              display: flex;
              align-items: center;
              padding: 2px 0;
            }

            &_count {
              margin: 0 0 0 5px;
              line-height: 1.3;
              font-size: 14px;
              font-weight: 300;
              color: rgba(0, 0, 0, 0.87);
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
