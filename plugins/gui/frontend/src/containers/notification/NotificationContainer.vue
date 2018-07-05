<template>
    <x-page title="notifications">
        <x-data-table module="notifications" title="Notifications" id-field="uuid" @click-row="navigateNotification" ref="table"/>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import xDataTable from '../../components/tables/DataTable.vue'

	import { mapState, mapActions } from 'vuex'
    import { FETCH_NOTIFICATION } from '../../store/modules/notifications'

	export default {
		name: 'notification-container',
        components: { xPage, xDataTable },
        computed: {
            ...mapState(['notification'])
        },
        methods: {
            ...mapActions({
                fetchNotification: FETCH_NOTIFICATION
            }),
            navigateNotification(notificationId) {
            	this.fetchNotification(notificationId)
                this.$router.push({path: `/notification/${notificationId}`})
            }
        },
        mounted() {
			this.$refs.table.fetchContentPages()
        }
	}
</script>

<style lang="scss">

</style>