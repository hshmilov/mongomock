<template>
  <XRoleGateway
    :permission-category="$permissionConsts.categories.Enforcements"
  >
    <template slot-scope="{ canAdd, canUpdate, canDelete }">
      <XPage
        title="Enforcement Center"
        class="x-enforcements"
        :class="{disabled: !canUpdate}"
      >
        <XSearch
          v-model="searchValue"
          placeholder="Search Enforcement Sets..."
          @keyup.enter.native="onSearchConfirm"
        />
        <XTable
          ref="table"
          v-model="selection"
          module="enforcements"
          title="Enforcement Sets"
          :fields="fields"
          :on-click-row="navigateEnforcement"
          :multiple-row-selection="canDelete"
        >
          <template slot="actions">
            <XButton
              v-if="hasSelection && canDelete"
              type="link"
              @click="remove"
            >
              Remove
            </XButton>
            <XButton
              id="enforcement_new"
              type="primary"
              :disabled="!canAdd"
              @click="newEnforcement('new')"
            >Add Enforcement</XButton>
            <XButton
              type="emphasize"
              :disabled="userCannotViewEnforcementsTasks"
              @click="navigateTasks"
            >View Tasks</XButton>
          </template>
        </XTable>
      </XPage>
    </template>
  </XRoleGateway>
</template>


<script>
import { mapState, mapMutations, mapActions } from 'vuex';
import XPage from '../axons/layout/Page.vue';
import XSearch from '../neurons/inputs/SearchInput.vue';
import XTable from '../neurons/data/Table.vue';
import XButton from '../axons/inputs/Button.vue';

import { UPDATE_DATA_VIEW } from '../../store/mutations';
import { REMOVE_ENFORCEMENTS, FETCH_ENFORCEMENT, SET_ENFORCEMENT } from '../../store/modules/enforcements';

export default {
  name: 'XEnforcements',
  components: {
    XPage, XSearch, XTable, XButton,
  },
  data() {
    return {
      selection: { ids: [], include: true },
      searchValue: '',
    };
  },
  computed: {
    ...mapState({
      query(state) {
        return state.enforcements.view.query;
      },
      isReadOnly(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Enforcements === 'ReadOnly';
      },
    }),
    name() {
      return 'enforcements';
    },
    fields() {
      return [{
        name: 'name', title: 'Name', type: 'string',
      }, {
        name: 'actions.main', title: 'Main Action', type: 'string',
      }, {
        name: 'triggers.view.name', title: 'Trigger Query Name', type: 'string',
      }, {
        name: 'triggers.last_triggered', title: 'Last Triggered', type: 'string', format: 'date-time',
      }, {
        name: 'triggers.times_triggered', title: 'Times Triggered', type: 'integer',
      }, {
        name: 'last_updated', title: 'Last Updated', type: 'string', format: 'date-time',
      }, {
        name: 'updated_by', title: 'Updated By', type: 'string',
      }];
    },
    hasSelection() {
      return (this.selection.ids && this.selection.ids.length) || this.selection.include === false;
    },
    numberOfSelections() {
      return this.selection.ids ? this.selection.ids.length : 0;
    },
    searchFilter() {
      const patternParts = [];
      this.fields.forEach((field) => {
        patternParts.push(`${field.name} == regex("${this.searchValue}", "i")`);
      });
      return patternParts.join(' or ');
    },
    userCannotViewEnforcementsTasks() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.View, this.$permissionConsts.categories.Tasks);
    },
  },
  created() {
    if (this.query) {
      this.searchValue = this.query.search;
    }
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      setEnforcement: SET_ENFORCEMENT,
    }),
    ...mapActions({
      removeEnforcements: REMOVE_ENFORCEMENTS, fetchEnforcement: FETCH_ENFORCEMENT,
    }),
    navigateEnforcement(enforcementId) {
      this.fetchEnforcement(enforcementId);
      this.$router.push({ path: `/${this.name}/${enforcementId}` });
    },
    newEnforcement(enforcementId) {
      this.setEnforcement();
      this.$router.push({ path: `/${this.name}/new` });
    },
    remove() {
      this.$safeguard.show({
        text: `
            The selected Enforcement ${this.numberOfSelections > 1 ? 'Sets' : 'Set'} will be completely removed from the system.
            <br />
            Removing the Enforcement ${this.numberOfSelections > 1 ? 'Sets' : 'Set'} is an irreversible action.
            <br />Do you wish to continue?
          `,
        confirmText: this.numberOfSelections > 1 ? 'Remove Enforcement Sets' : 'Remove Enforcement Set',
        onConfirm: () => {
          this.removeEnforcements(this.selection);
          this.selection = { ids: [], include: true };
        },
      });
    },
    navigateTasks() {
      this.updateView({
        module: 'tasks',
        view: {
          query: {
            filter: '',
          },
        },
      });
      this.$router.push({ name: 'Tasks' });
    },
    onSearchConfirm() {
      this.updateView({
        module: this.name,
        view: {
          query: {
            filter: this.searchFilter,
            search: this.searchValue,
          },
          page: 0,
        },
      });
      this.$refs.table.fetchContentPages(true);
    },
  },
};
</script>


<style lang="scss">
    .x-enforcements {
        .x-button {
            width: auto;
        }
    }
</style>
