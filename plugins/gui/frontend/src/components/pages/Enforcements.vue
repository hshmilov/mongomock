<template>
  <XRoleGateway
    :permission-category="$permissionConsts.categories.Enforcements"
  >
    <template slot-scope="{ canAdd, canUpdate, canDelete }">
      <XPage
        title="Enforcement Center"
        class="x-enforcements"
        :class="{disabled: !canUpdate || enforcementsLocked}"
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
          :multiple-row-selection="canDelete && !enforcementsLocked"
        >
          <template slot="actions">
            <XButton
              v-if="hasSelection && canDelete"
              type="link"
              @click="remove"
            >Delete</XButton>
            <XButton
              id="enforcement_new"
              type="primary"
              :disabled="!canAdd || !canUpdate || enforcementsLocked"
              @click="newEnforcement('new')"
            >Add Enforcement</XButton>
            <XButton
              type="emphasize"
              :disabled="userCannotViewEnforcementsTasks || enforcementsLocked"
              @click="navigateTasks"
            >View Tasks</XButton>
          </template>
        </XTable>
        <XEnforcementsFeatureLockTip
          :enabled="enforcementsLocked"
        />
      </XPage>
    </template>
  </XRoleGateway>
</template>


<script>
import { mapState, mapMutations, mapActions } from 'vuex';
import _get from 'lodash/get';

import XEnforcementsFeatureLockTip from '@networks/enforcement/EnforcementsFeatureLockTip.vue';
import XPage from '@axons/layout/Page.vue';
import XSearch from '@neurons/inputs/SearchInput.vue';
import XTable from '@neurons/data/Table.vue';
import XButton from '@axons/inputs/Button.vue';
import { actionsMeta } from '@constants/enforcement';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import { REMOVE_ENFORCEMENTS, SET_ENFORCEMENT } from '@store/modules/enforcements';

export default {
  name: 'XEnforcements',
  components: {
    XPage, XSearch, XTable, XButton, XEnforcementsFeatureLockTip,
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
      enforcementsLocked(state) {
        return !_get(state, 'settings.configurable.gui.FeatureFlags.config.enforcement_center', true);
      },
      triggerPeriods(state) {
        return _get(state, 'constants.constants.trigger_periods', []);
      },
    }),
    name() {
      return 'enforcements';
    },
    fields() {
      return [
        {
          name: 'name',
          title: 'Name',
          type: 'string',
        },
        {
          name: 'actions.main',
          title: 'Main Action Name',
          type: 'string',
        },
        {
          name: 'actions.main.type',
          title: 'Main Action Type',
          type: 'string',
          cellRenderer: (mainActionType) => (actionsMeta[mainActionType].title),
        },
        {
          name: 'triggers.view.name',
          title: 'Trigger Query Name',
          type: 'string',
        },
        {
          name: 'triggers.period',
          title: 'Trigger Schedule',
          type: 'string',
          cellRenderer: (period) => (this.getPeriodDescription(period)),
        },
        {
          name: 'triggers.last_triggered',
          title: 'Last Triggered',
          type: 'string',
          format: 'date-time',
        },
        {
          name: 'triggers.times_triggered',
          title: 'Times Triggered',
          type: 'integer',
        },
        {
          name: 'last_updated',
          title: 'Last Updated',
          type: 'string',
          format: 'date-time',
        },
        {
          name: 'updated_by',
          title: 'Updated By',
          type: 'string',
          format: 'user',
        },
      ];
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
      removeEnforcements: REMOVE_ENFORCEMENTS,
    }),
    navigateEnforcement(enforcementId) {
      if (this.enforcementsLocked) return;
      this.$router.push({ path: `/${this.name}/${enforcementId}` });
    },
    newEnforcement() {
      this.setEnforcement();
      this.$router.push({ path: `/${this.name}/new` });
    },
    remove() {
      const numberPostfix = this.numberOfSelections > 1 ? 'Sets' : 'Set';
      this.$safeguard.show({
        text: `
            The selected Enforcement ${numberPostfix} will be completely deleted from the system.
            <br />
            Deleting the Enforcement ${numberPostfix} is an irreversible action.
            <br />Do you wish to continue?
          `,
        confirmText: this.numberOfSelections > 1 ? 'Delete Enforcement Sets' : 'Delete Enforcement Set',
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
    getPeriodDescription(period) {
      const relevantPeriod = this.triggerPeriods.find((x) => x[period]);
      if (relevantPeriod) {
        return relevantPeriod[period];
      }
      return period;
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
