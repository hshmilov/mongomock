<template>
    <x-page class="x-tasks" :breadcrumbs="[
        { title: 'enforcement center', path: { name: 'Enforcements'}},
    	{ title: 'enforcement tasks' }]" beta>

        <x-table module="tasks" @click-row="viewTask" title="Enforcement Tasks" />
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../neurons/data/Table.vue'

    import {mapActions} from 'vuex'
    import {FETCH_TASK} from '../../store/modules/tasks'

    export default {
        name: 'x-tasks',
        components: {
            xPage, xTable
        },
        methods: {
            ...mapActions({
                fetchTask: FETCH_TASK
            }),
            viewTask(taskId) {
                this.fetchTask(taskId)
                this.$router.push({path: `/enforcements/tasks/${taskId}`})
            }
        }
    }
</script>

<style lang="scss">

</style>