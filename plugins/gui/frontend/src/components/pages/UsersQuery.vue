<template>
    <x-page title="saved queries">
        <x-queries-table module="users" :read-only="isReadOnly"/>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xQueriesTable from '../networks/entities/QueriesTable.vue'

    import {mapState} from 'vuex'

    export default {
        name: 'x-users-query',
        components: {
            xPage, xQueriesTable
        },
        computed: mapState({
            isReadOnly(state) {
                let user = state.auth.currentUser.data
                if (!user || !user.permissions) return true
                return user.permissions.Users === 'ReadOnly'
            }

        })
    }
</script>

<style lang="scss">

</style>