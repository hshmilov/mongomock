<template>
  <XRoleGateway
    :permission-category="$permissionConsts.categories.Reports"
  >
    <template slot-scope="{ canAdd, canDelete }">
      <XPage
        class="x-reports"
        title="Reports"
      >
        <XTable
          v-model="selection"
          :fields="fields"
          :on-click-row="navigateReport"
          module="reports"
          title="Reports"
          :multiple-row-selection="canDelete"
        >
          <template slot="actions">
            <XButton
              v-if="hasSelection"
              type="link"
              @click="remove"
            >
              Remove
            </XButton>
            <XButton
              id="report_new"
              type="primary"
              :disabled="!canAdd"
              @click="navigateReport('new')"
            >Add Report</XButton>
          </template>
        </XTable>
      </XPage>
    </template>
  </XRoleGateway>
</template>
<script>
import { mapState, mapActions } from 'vuex';
import XPage from '../axons/layout/Page.vue';
import XTable from '../neurons/data/Table.vue';
import XButton from '../axons/inputs/Button.vue';

import { REMOVE_REPORTS, FETCH_REPORT } from '../../store/modules/reports';

export default {
  name: 'XReports',
  components: { XPage, XTable, XButton },
  computed: {
    ...mapState({
      isReadOnly(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Reports === 'ReadOnly';
      },
    }),
    name() {
      return 'reports';
    },
    fields() {
      return [{
        name: 'name', title: 'Name', type: 'string',
      }, {
        name: 'last_generated', title: 'Last Generated', type: 'string', format: 'date-time',
      }, {
        name: 'mailSubject', title: 'Email Subject', type: 'string',
      }, {
        name: 'period', title: 'Scheduled Email', type: 'string',
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
  },
  data() {
    return {
      selection: {
        ids: [], include: true,
      },
    };
  },
  methods: {
    ...mapActions({
      removeReports: REMOVE_REPORTS, fetchReport: FETCH_REPORT,
    }),
    navigateReport(reportId) {
      this.fetchReport(reportId);
      this.$router.push({ path: `/${this.name}/${reportId}` });
    },
    remove() {
      this.$safeguard.show({
        text: `
                  The selected ${this.numberOfSelections > 1 ? 'reports' : 'report'} will be completely removed
                  from the system.<br/>
                  Removing the ${this.numberOfSelections > 1 ? 'reports' : 'report'} is an irreversible action.<br/>
                  Do you wish to continue?
                  `,
        confirmText: 'Remove Reports',
        onConfirm: () => {
          this.removeReports(this.selection);
          this.selection = { ids: [], include: true };
        },
      });
    },
  },
};
</script>


<style lang="scss">
    .x-reports {
        .x-button {
            width: auto;
        }
    }
</style>
