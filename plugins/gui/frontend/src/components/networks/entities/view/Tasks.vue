<template>
  <XTable
    :title="actionFields.title"
    :module="module"
    :fields="actionFields.items"
    :static-data="processedTasks"
    id-field="action_id"
  >
    <template
      #search="{ onSearch, tableTitle, tableModule, tableView }"
    >
      <XTableSearchFilters
        :module="tableModule"
        :view="tableView"
        :search-placeholder="tableTitle"
        @search="onSearch"
      />
    </template>
    <template slot="actions">
      <XButton
        type="link"
        class="entityMenu"
        :disabled="exportInProgress"
        @click="exportCSV"
      >
        <template v-if="exportInProgress">
          <XIcon type="loading" />Exporting...
        </template>
        <template v-else>Export CSV</template>
      </XButton>
    </template>
  </XTable>
</template>

<script>
import { mapActions } from 'vuex';
import XTableSearchFilters from '@neurons/inputs/TableSearchFilters.vue';
import XTable from '@neurons/data/Table.vue';

import { actionsMeta } from '@constants/enforcement';
import { FETCH_DATA_CONTENT_CSV } from '@store/actions';

export default {
  name: 'XEntityTasks',
  components: {
    XTable, XTableSearchFilters,
  },
  props: {
    entityType: {
      type: String,
      required: true,
    },
    entityId: {
      type: String,
      required: true,
    },
    tasks: {
      type: Array,
      required: true,
    },
    module: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      exportInProgress: false,
    };
  },
  computed: {
    actionFields() {
      const actionsFields = {
        name: 'enforcement_task',
        title: 'Enforcement tasks actions',
        items: [
          {
            name: 'recipe_name',
            title: 'Task Name',
            type: 'string',
            link: '/tasks/{{uuid}}',
          },
          {
            name: 'action_name',
            title: 'Action Name',
            type: 'string',
          },
          {
            name: 'action_type',
            title: 'Action Type',
            type: 'string',
          },
          {
            name: 'success',
            title: 'Success',
            type: 'bool',
          },
          {
            name: 'additional_info',
            title: 'Additional Info',
            type: 'string',
          },
        ],
      };
      if (this.cannotViewEnforcementTasks) {
        delete actionsFields.items[0].link;
      }
      return actionsFields;
    },
    processedTasks() {
      return this.tasks.map((task) => {
        if (!actionsMeta[task.action_type]) {
          return task;
        }
        return {
          ...task,
          action_type: actionsMeta[task.action_type].title,
        };
      });
    },
    cannotViewEnforcementTasks() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.View,
        this.$permissionConsts.categories.Tasks)
        || this.$cannot(this.$permissionConsts.categories.Enforcements,
          this.$permissionConsts.actions.View);
    },
  },
  methods: {
    ...mapActions({
      fetchDataCSV: FETCH_DATA_CONTENT_CSV,
    }),
    exportCSV() {
      this.exportInProgress = true;
      this.fetchDataCSV({
        module: this.module,
        endpoint: `${this.entityType}/${this.entityId}/tasks`,
        schema_fields: this.actionFields.items,
      }).then(() => {
        this.exportInProgress = false;
      });
    },
  },
};
</script>
