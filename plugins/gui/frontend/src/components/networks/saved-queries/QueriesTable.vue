<template>
  <div class="x-queries-table">
    <section class="queries-table-header">
      <div class="queries-table-header__search">
        <XSearch
          v-model="searchValue"
          class="search__input"
          placeholder="Search Queries..."
          @keyup.enter.native="applySearchAndFilter"
        />
        <div class="tags-filter">
          <XCombobox
            v-if="entityTags.length"
            v-model="filterTags"
            height="30"
            :selection-display-limit="1"
            :items="entityTags"
            label="Tags"
            multiple
            :allow-create-new="false"
            :hide-quick-selections="false"
            :prepend-icon="filterIcon"
            :menu-props="{maxWidth: 300}"
            @change="applySearchAndFilter"
          />
        </div>
        <XSwitch
          :checked="showPrivateOnly"
          class="private-switch"
          label="Private queries only"
          @change="togglePrivateSwitch"
        />
        <XButton
          class="search__reset"
          type="link"
          @click="resetSearchAndFilters"
        >Reset</XButton>
      </div>
      <XButton
        type="link"
        icon="question-circle"
        @click="openAxoniusDocs"
      >Learn about Axonius use cases</XButton>
    </section>
    <XSavedQueriesPanel
      v-model="isPanelOpen"
      :namespace="namespace"
      @input="panelStateChanged"
      @run="runQuery"
      @delete="handleSelectedQueriesDeletion"
      @save-changes="saveQueryChanges"
      @close="closeQuerySidePanel"
      @new-enforcement="createEnforcement"
      @set-public="setQueryPublic"
    />
    <XTable
      ref="table"
      v-model="queriesRowsSelections"
      :module="pathToSavedQueryInState"
      title="Saved Queries"
      :fields="queriesTableFieldsSchema"
      :on-click-row="openQuerySidePanel"
    >
      <template slot="actions">
        <XButton
          v-if="hasSelection"
          id="remove-queries-btn"
          type="link"
          :disabled="userCannotDeleteSavedQueries"
          @click="handleSelectedQueriesDeletion"
        >Delete</XButton>
      </template>
    </XTable>
    <XEnforcementsFeatureLockTip
      :enabled="showEnforcementsLockTip"
      @close-lock-tip="closeEnforcementsLockTip"
    />
  </div>
</template>

<script>
import { mapState, mapMutations, mapActions } from 'vuex';
import { mdiFilter } from '@mdi/js';
import _debounce from 'lodash/debounce';
import XSearch from '@neurons/inputs/SearchInput.vue';
import XTable from '@neurons/data/Table.vue';
import XButton from '@axons/inputs/Button.vue';
import XSwitch from '@axons/inputs/Switch.vue';
import XSavedQueriesPanel from '@networks/saved-queries/SavedQueryPanel';
import XCombobox from '@axons/inputs/combobox/index.vue';
import XEnforcementsFeatureLockTip from '@networks/enforcement/EnforcementsFeatureLockTip.vue';

import { UPDATE_DATA_VIEW } from '@store/mutations';
import { DELETE_DATA, SAVE_VIEW, PUBLISH_VIEW } from '@store/actions';
import { SET_ENFORCEMENT, initTrigger } from '@store/modules/enforcements';

import { fetchEntityTags } from '@api/saved-queries';
import { getEntityPermissionCategory } from '@constants/entities';
import _get from 'lodash/get';

export default {
  name: 'XQueriesTable',
  components: {
    XSearch, XTable, XButton, XSavedQueriesPanel, XCombobox, XEnforcementsFeatureLockTip, XSwitch,
  },
  props: {
    namespace: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      isPanelOpen: false,
      selection: { ids: [], include: true },
      searchValue: '',
      entityTags: [],
      filterTags: [],
      showEnforcementsLockTip: false,
      showPrivateOnly: false,
    };
  },
  computed: {
    ...mapState({
      savedQueries(state) {
        return state[this.namespace].views.saved.content.data;
      },
      permissionCategory() {
        return getEntityPermissionCategory(this.namespace);
      },
      userCannotDeleteSavedQueries() {
        return this.$cannot(this.permissionCategory,
          this.$permissionConsts.actions.Delete, this.$permissionConsts.categories.SavedQueries);
      },
      enforcementsLocked(state) {
        return !_get(state, 'settings.configurable.gui.FeatureFlags.config.enforcement_center', true);
      },
    }),
    queriesRowsSelections: {
      get() {
        return this.userCannotDeleteSavedQueries ? undefined : this.selection;
      },
      set(newSelections) {
        this.selection = newSelections;
      },
    },
    pathToSavedQueryInState() {
      return `${this.namespace}/views/saved`;
    },
    hasSelection() {
      return (this.selection.ids && this.selection.ids.length) || this.selection.include === false;
    },
    numberOfSelections() {
      return this.selection.ids ? this.selection.ids.length : 0;
    },
    queriesTableFieldsSchema() {
      return [
        {
          name: 'name',
          title: 'Name',
          type: 'string',
        },
        {
          name: 'tags',
          title: 'Tags',
          type: 'array',
          items: {
            format: 'tag',
            type: 'string',
          },
        },
        {
          name: 'private',
          title: 'Access',
          type: 'bool',
          cellRenderer: (isPrivate) => (isPrivate ? 'Private' : 'Public'),
        },
        {
          name: 'last_updated', title: 'Last Updated', type: 'string', format: 'date-time',
        },
        {
          name: 'updated_by', title: 'Updated By', type: 'string', format: 'user',
        },
      ];
    },
    searchFilter() {
      const queryStringParts = [];
      if (this.searchValue) {
        queryStringParts.push(`(name == regex("${this.searchValue}", "i"))`);
      } if (this.filterTags.length) {
        queryStringParts.push(`tags in ["${this.filterTags.join('","')}"]`);
      } if (this.showPrivateOnly) {
        queryStringParts.push(`(private == ${true})`);
      }

      return queryStringParts.join(' and ');
    },
    filterIcon() {
      return this.filterTags.length ? mdiFilter : '';
    },
  },
  watch: {
    $route(to) {
      const { params: { queryId } } = to;
      if (queryId) {
        this.isPanelOpen = true;
        this.selection.ids = [queryId];
      } else {
        this.isPanelOpen = false;
        this.selection.ids = [];
      }
    },
  },
  mounted() {
    const { queryId } = this.$route.params;
    this.fetchTagsApi();
    if (queryId) {
      this.isPanelOpen = true;
      this.selection.ids = [queryId];
    }
  },
  methods: {
    async saveQueryChanges({ queryData, done }) {
      try {
        await this.updateQuery({
          module: this.namespace,
          ...queryData,
        });
        this.fetchTagsApi();
        done();
      } catch (ex) {
        done(ex);
      }
    },
    async fetchTagsApi() {
      this.entityTags = [];
      try {
        const tags = await fetchEntityTags(this.namespace);
        this.entityTags = tags;
      } catch (ex) {
        console.warn('featch tags failed');
      }
    },
    runQuery(viewId) {
      const selectedView = this.savedQueries.find((view) => view.uuid === viewId);
      this.updateView({
        module: this.namespace,
        view: { ...selectedView.view, enforcement: null },
        selectedView: {
          uuid: selectedView.uuid,
          filter: selectedView.view.query.filter,
        },
      });

      this.$router.push({ path: `/${this.namespace}` });
    },
    createEnforcement(queryId) {
      if (this.enforcementsLocked) {
        this.closeQuerySidePanel();
        this.openEnforcementsLockTip();
        return;
      }

      this.setEnforcement({
        actions: {
          main: null,
          success: [],
          failure: [],
          post: [],
        },
        triggers: [{
          ...initTrigger,
          name: 'Trigger',
          view: {
            id: queryId, entity: this.namespace,
          },
        }],
      });
      /* Navigating to new enforcement - requested queries will be selected as triggers there */
      this.$router.push({ path: '/enforcements/new' });
    },
    async handleSelectedQueriesDeletion(e, queryId, isPrivate) {
      if (queryId) {
        // The remover invoked from within the panel and the panel should be closed.
        this.closeQuerySidePanel();
      }
      this.$safeguard.show({
        text: `
            The selected Saved ${this.numberOfSelections > 1 ? 'Queries' : 'Query'} will be completely deleted from the
            system and no other user will be able to use it.
            <br />
            Deleting the Saved ${this.numberOfSelections > 1 ? 'Queries' : 'Query'} is an irreversible action.
            <br />Do you wish to continue?
          `,
        confirmText: this.numberOfSelections > 1 ? 'Delete Saved Queries' : 'Delete Saved Query',
        onConfirm: async () => {
          try {
            await this.removeData({
              module: this.pathToSavedQueryInState,
              selection: !queryId ? this.selection : {
                ids: [queryId],
                include: true,
                private: isPrivate,
              },
            });
            this.updateCurrentView();
            this.closeQuerySidePanel();
          } catch (ex) {
            console.error(ex);
          }
        },
      });
    },
    async setQueryPublic({ queryData, done }) {
      this.$safeguard.show({
        text: `
            The selected Saved Query will become publicly available to all users and cannot be reset to private.
            <br />
            Do you wish to continue?
          `,
        confirmText: 'Set Public',
        onConfirm: async () => {
          try {
            await this.publishQuery({
              module: this.namespace,
              ...queryData,
            });
            this.updateCurrentView();
            done();
          } catch (ex) {
            console.error(ex);
            done();
          }
        },
        onCancel: () => {
          done();
        },
      });
    },
    panelStateChanged(open) {
      if (!open) {
        this.$router.push({ name: `${this.namespace}-queries` });
        this.fetchTagsApi();
        this.resetTableSelections();
      }
    },
    openQuerySidePanel(selectedQueryId) {
      this.isPanelOpen = !this.isPanelOpen;
      this.selection = { ids: [selectedQueryId], include: true };
      this.$router.push({ path: '', params: { queryId: selectedQueryId } });
    },
    closeQuerySidePanel() {
      this.isPanelOpen = false;
    },
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW, setEnforcement: SET_ENFORCEMENT,
    }),
    ...mapActions({
      removeData: DELETE_DATA,
      updateQuery: SAVE_VIEW,
      publishQuery: PUBLISH_VIEW,
    }),
    resetSearchAndFilters() {
      this.searchValue = '';
      this.filterTags = [];
      this.showPrivateOnly = false;
      this.updateCurrentView();
    },
    openAxoniusDocs() {
      window.open('https://docs.axonius.com/docs/use-cases', '_blank');
    },
    resetTableSelections() {
      this.selection.ids = [];
    },
    applySearchAndFilter: _debounce(function applySearchAndFilter() {
      this.updateCurrentView();
    }, 250),
    updateCurrentView() {
      this.resetTableSelections();
      this.updateView({
        module: this.pathToSavedQueryInState,
        view: {
          query: {
            filter: this.searchFilter,
          },
          page: 0,
        },
      });
      this.$refs.table.fetchContentPages(true);
    },
    openEnforcementsLockTip() {
      this.showEnforcementsLockTip = true;
    },
    closeEnforcementsLockTip() {
      this.showEnforcementsLockTip = false;
    },
    togglePrivateSwitch() {
      this.showPrivateOnly = !this.showPrivateOnly;
      this.applySearchAndFilter();
    },
  },
};
</script>

<style lang="scss">
  .x-queries-table {
    height: 100%;

    .table-td-name {
      width: 850px;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .table-td-tags {
      width: 400px;
    }
  }

  .queries-table-header {
    display: flex;
    justify-content: space-between;
    .queries-table-header__search {
      display: flex;
      align-items: flex-end;
      .search__input {
        line-height: 32px;
        height: 32px;
        width: 400px;

        .input-icon {
          top: 0;
          left: 4px;
        }
      }
      .tags-filter {
        width: 300px;
        margin-left: 40px;
        .x-combobox {
          font-size: 14px;

          .v-input__control {
            border: 1px solid #DEDEDE !important;
          }
        }
      }
      .search__reset {
        margin-left: 16px;
      }
      .private-switch {
        margin: 0 0 4px 36px;
      }
    }
  }

</style>
