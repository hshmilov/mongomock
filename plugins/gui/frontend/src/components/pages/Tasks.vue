<template>
  <x-page class="x-tasks" :breadcrumbs="breadcrumbs">
    <x-search
      v-model="searchValue"
      placeholder="Search Tasks..."
      @keyup.enter.native="onSearchConfirm"
    />
    <x-table
      :module="enforcementDesignated ? 'enforcements/current' : 'tasks'"
      :endpoint="endpointForDesignatedTasks"
      title="Enforcement Tasks"
      :static-fields="fields"
      :on-click-row="viewTask"
    />
  </x-page>
</template>

<script>
  import xPage from '../axons/layout/Page.vue'
  import xSearch from '../neurons/inputs/SearchInput.vue'
  import xSelect from '../axons/inputs/Select.vue'
  import xTable from '../neurons/data/Table.vue'

  import { mapMutations, mapActions, mapState } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../store/mutations'
  import { FETCH_TASK } from '../../store/modules/tasks'

  import { FETCH_ENFORCEMENT } from '../../store/modules/enforcements'

  export default {
    name: 'XTasks',
    components: {
      xPage, xSearch, xSelect, xTable
    },
    computed: {
      ...mapState({
        currentEnforcementName(state) {
          return state.enforcements.current.data.name
        }
      }),
      enforcementDesignated() {
        return this.$route.params.id || false
      },
      endpointForDesignatedTasks(){
        return this.enforcementDesignated ? `enforcements/${this.enforcementDesignated}/tasks` : ''
      },
      breadcrumbs() {
        return [
          { title: 'enforcement center', path: { name: 'Enforcements'}},
          ...( this.enforcementDesignated ? [{title: this.currentEnforcementName, path: { name: 'Enforcement', params: {id: this.enforcementDesignated}}}] : [] ),
          { title: 'Tasks' }
        ]        
      },
      fields() {
        return [{
          name: 'status', title: 'Status', type: 'string'
        }, {
          name: 'result.metadata.success_rate', title: 'Successful / Total', type: 'string'
        }, {
          name: 'post_json.report_name', title: 'Name', type: 'string'
        }, {
          name: 'result.main.name', title: 'Main Action', type: 'string'
        }, {
          name: 'result.metadata.trigger.view.name', title: 'Trigger Query Name', type: 'string'
        }, {
          name: 'started_at', title: 'Started', type: 'string', format: 'date-time'
        }, {
          name: 'finished_at', title: 'Completed', type: 'string', format: 'date-time'
        }]
      },
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
        let textFilter = this.fields.map(field => `${field.name} == regex("${this.searchValue}", "i")`).join(' or ')
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
    created() {
      this.fetchEnforcementIfNotExist()
      this.onSearchConfirm()
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      ...mapActions({
        fetchTask: FETCH_TASK,
        fetchEnforcmentAPI: FETCH_ENFORCEMENT,
      }),
      fetchEnforcementIfNotExist() {

        if(!this.currentEnforcementName) {
          this.fetchEnforcmentAPI(this.enforcementDesignated)
        }
      },
      viewTask (taskId) {
        this.fetchTask(taskId)
        this.$router.push({ path: `/enforcements/tasks/${taskId}` })
      },
      onSearchConfirm() {
        this.updateView({
          module: this.enforcementDesignated ? 'enforcements/current' : 'tasks',
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