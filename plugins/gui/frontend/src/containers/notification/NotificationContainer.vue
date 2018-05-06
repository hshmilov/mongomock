<template>
    <x-page title="notifications">
        <card :title="`notifications (${notification.notificationList.data.length})`">
            <paginated-table slot="cardContent" :fetching="notification.notificationList.fetching"
                             :data="notification.notificationList.data" :error="notification.notificationList.error"
                             :fields="notification.fields" :fetchData="fetchNotifications"
                             @click-row="navigateNotification" idField="uuid"></paginated-table>
        </card>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import Card from '../../components/Card.vue'
    import PaginatedTable from '../../components/tables/PaginatedTable.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { RESTART_NOTIFICATIONS, FETCH_NOTIFICATIONS, FETCH_NOTIFICATION } from '../../store/modules/notifications'

	export default {
		name: 'notification-container',
        components: { xPage, Card, PaginatedTable },
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
                this.$router.push({path: `/notification/${notificationId}`})
            }
        },
        created () {
		    this.fetchNotifications()
        }
	}
</script>

<style lang="scss">

</style>