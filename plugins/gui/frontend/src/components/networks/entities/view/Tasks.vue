<template>
  <x-tabs :vertical="true">
    <x-tab
      v-for="(task, i) in tasks"
      :id="`task_${i}`"
      :key="`task_${i}`"
      :title="`${task.recipe_name} - Task ${task.recipe_pretty_id}`"
      :selected="!i"
    >
      <x-table
        :data="processTaskActions(task.actions)"
        :fields="actionFields"
      />
    </x-tab>
  </x-tabs>
</template>

<script>
  import xTabs from '../../../axons/tabs/Tabs.vue'
  import xTab from '../../../axons/tabs/Tab.vue'
  import xTable from '../../../axons/tables/Table.vue'

  import {actionsMeta} from '../../../../constants/enforcement'

  export default {
    name: 'XEntityTasks',
    components: {
      xTabs, xTab, xTable
    },
    props: {
      tasks: {
        type: Array,
        required: true
      }
    },
    computed: {
      actionFields() {
        return [
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
            'title': 'Result',
            'type': 'bool'
          },
          {
            'name': 'additional_info',
            'title': 'Additional Info',
            'type': 'string'
          },
        ]
      }
    },
    methods: {
      processTaskActions(actions) {
        return actions.map(action => {
          if (!actionsMeta[action.action_type]) return action
          return {...action,
            action_type: actionsMeta[action.action_type].title
          }
        })
      }
    }
  }
</script>

<style lang="scss">

</style>