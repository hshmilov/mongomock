<template>
  <x-page
    class="x-tasks"
    :breadcrumbs="[
      { title: 'enforcement center', path: { name: 'Enforcements'}},
      { title: 'enforcement tasks' }]"
    beta
  >
    <div class="tasks-search">
      <x-search
        v-model="searchValue"
        placeholder="Search Tasks..."
        @keyup.enter.native="onSearchConfirm"
      />
      <label>Status:</label>
      <x-select
        v-model="statusValue"
        :options="statusOptions"
        @input="onSearchConfirm"
      />
    </div>
    <x-table
      module="tasks"
      title="Enforcement Tasks"
      @click-row="viewTask"
    />
  </x-page>
</template>

<script>
  import xPage from '../axons/layout/Page.vue'
  import xSearch from '../neurons/inputs/SearchInput.vue'
  import xSelect from '../axons/inputs/Select.vue'
  import xTable from '../neurons/data/Table.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../store/mutations'
  import { FETCH_TASK } from '../../store/modules/tasks'

  export default {
    name: 'XTasks',
    components: {
      xPage, xSearch, xSelect, xTable
    },
    computed: {
      ...mapState({
        searchFields (state) {
          return state.tasks.view.fields
        }
      }),
      statusOptions() {
        return [{
          name: '*', title: 'Any'
        }, {
          name: 'Successful', title: 'Completed'
        }, {
          name: 'Running', title: 'In Progress'
        }]
      },
      searchFilter() {
        let textFilter = this.searchFields.map(field => `${field} == regex("${this.searchValue}", "i")`).join(' or ')
        if (this.statusValue === '*') {
          return textFilter
        }
        return `job_completed_state == '${this.statusValue}' and (${textFilter})`
      }
    },
    data () {
      return {
        searchValue: '',
        statusValue: '*'
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      ...mapActions({
        fetchTask: FETCH_TASK
      }),
      viewTask (taskId) {
        this.fetchTask(taskId)
        this.$router.push({ path: `/enforcements/tasks/${taskId}` })
      },
      onSearchConfirm() {
        this.updateView({
          module: 'tasks',
          view: {
            query: {
              filter: this.searchFilter
            },
            page: 0
          }
        })
      }
    }
  }
</script>

<style lang="scss">
  .x-tasks {
    .tasks-search {
      display: flex;
      align-items: center;
      .x-search-input {
        width: 480px;
        margin-right: 24px;
      }
      .x-select {
        min-width: 120px;
        margin-left: 8px;
      }
    }
  }
</style>