<template>
    <x-page title="saved queries">
        <x-data-queries-table module="users" :read-only="isReadOnly" />
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xDataQueriesTable from '../../components/data/DataQueriesTable.vue'

    import { mapState } from 'vuex'

	export default {
		name: 'user-queries-container',
        components: {
            xPage, xDataQueriesTable
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