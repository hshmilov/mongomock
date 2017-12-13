<template>
    <scrollable-page :breadcrumbs="[
    	{title: 'notifications', path: {'name': 'Notifications'}},
        {title: notification.notificationDetails.data.title}
        ]">
        <card>
            <div slot="cardContent">{{notification.notificationDetails.data.content}}</div>
        </card>
    </scrollable-page>
</template>

<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
	import Card from '../../components/Card.vue'

	import { mapState, mapActions } from 'vuex'
	import { FETCH_NOTIFICATION, UPDATE_NOTIFICATIONS_SEEN } from '../../store/modules/notifications'

	export default {
		name: 'notification-view-container',
		components: {ScrollablePage, Card},
		computed: {
			...mapState(['notification']),
			notificationId () {
				return this.$route.params.id
			}
		},
        watch: {
			notificationId(newNotificationId) {
				if (!this.notification.notificationDetails.data.seen) {
					this.updateNotificationsSeen([ newNotificationId ])
				}
            }
        },
		methods: {
			...mapActions({fetchNotification: FETCH_NOTIFICATION, updateNotificationsSeen: UPDATE_NOTIFICATIONS_SEEN })
		},
		mounted () {
			/*
			    Refresh or navigation directly to the url, will cause missing or incorrect notification data.
			    This condition should identify the situation and re-fetch the notification
			 */
			if (!this.notification.notificationDetails.data || !this.notification.notificationDetails.data.uuid
                || (this.notification.notificationDetails.data.uuid !== this.notificationId)) {
				this.fetchNotification(this.notificationId)
			}
		}
	}
</script>

<style lang="scss">

</style>