<template>
    <scrollable-page title="notifications">
        <card :title="`notifications (${notification.notificationList.data.length})`">
            <paginated-table slot="cardContent" :fetching="notification.notificationList.fetching"
                             :data="notification.notificationList.data" :error="notification.notificationList.error"
                             :fields="notification.fields" :fetchData="fetchNotifications"
                             @click-row="navigateNotification" idField="uuid"></paginated-table>
        </card>
    </scrollable-page>
</template>

<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
	import Card from '../../components/Card.vue'
    import PaginatedTable from '../../components/PaginatedTable.vue'
    import InfoDialog from '../../components/popover/InfoDialog.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { RESTART_NOTIFICATIONS, FETCH_NOTIFICATIONS, FETCH_NOTIFICATION } from '../../store/modules/notifications'

	export default {
		name: 'notification-container',
        components: { ScrollablePage, Card, PaginatedTable },
        computed: {
            ...mapState(['notification'])
        },
        methods: {
            ...mapMutations({ restartNotifications: RESTART_NOTIFICATIONS }),
            ...mapActions({
                fetchNotifications: FETCH_NOTIFICATIONS,
                fetchNotification: FETCH_NOTIFICATION
            }),
            navigateNotification(notificationId) {
            	this.fetchNotification(notificationId)
                this.$router.replace({path: `/notification/${notificationId}`})
            }
        }
	}
</script>

<style lang="scss">

</style>