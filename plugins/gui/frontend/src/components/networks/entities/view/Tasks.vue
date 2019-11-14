<template>
  <x-table
    :title="actionFields.title"
    :module="module"
    :static-fields="actionFields.items"
    :static-data="processTaskActions(tasks)"
    :searchable="true"
    id-field="action_id"
  >
    <template slot="actions">
      <x-button
        link
        @click="exportCSV"
      >Export CSV</x-button>
    </template>
  </x-table>
</template>

<script>
  import xTable from '../../../neurons/data/Table.vue'
  import xButton from '../../../axons/inputs/Button.vue'

  import {actionsMeta} from '../../../../constants/enforcement'
  import { mapActions } from 'vuex'
  import { FETCH_DATA_CONTENT_CSV } from '../../../../store/actions'

  export default {
    name: 'XEntityTasks',
    components: {
      xTable, xButton
    },
    props: {
      entityType: {
          type: String,
          required: true
      },
      entityId: {
          type: String,
          required: true
      },
      tasks: {
        type: Array,
        required: true
      },
      module: {
          type: String,
          required: true
      }
    },
    computed: {
      actionFields() {
        return {
            'name': 'enforcement_task',
            'title': 'Enforcement tasks actions',
            'items': [
              {
                  'name': 'recipe_name',
                  'title': 'Task Name',
                  'type': 'string',
                  'link': '/tasks/{{uuid}}'
              },
              {
                'name': 'action_name',
                'title': 'Action Name',
                'type': 'string'
              },
              {
                'name': 'action_type',
                'title': 'Action Type',
                'type': 'string'
              },
              {
                'name': 'success',
                'title': 'Success',
                'type': 'bool'
              },
              {
                'name': 'additional_info',
                'title': 'Additional Info',
                'type': 'string'
              }
            ]
        }
      }
    },
    methods: {
      ...mapActions({
          fetchDataCSV: FETCH_DATA_CONTENT_CSV
      }),
      processTaskActions(actions) {
        return actions.map(action => {
          if (!actionsMeta[action.action_type]) return action
          return {...action,
            action_type: actionsMeta[action.action_type].title
          }
        })
      },
      exportCSV () {
          this.fetchDataCSV({
              module: this.module,
              endpoint: `${this.entityType}/${this.entityId}/tasks`
          })
      }
    }
  }
</script>
