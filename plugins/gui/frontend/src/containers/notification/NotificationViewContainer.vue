<template>
    <x-page :breadcrumbs="[
    	{title: 'notifications', path: {'name': 'Notifications'}},
        {title: notification.notificationDetails.data.title}
        ]">
        <card>
            <div slot="cardContent">{{notification.notificationDetails.data.content}}</div>
        </card>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import Card from '../../components/Card.vue'

	import { mapState, mapActions } from 'vuex'
	import { FETCH_NOTIFICATION, UPDATE_NOTIFICATIONS_SEEN } from '../../store/modules/notifications'

	export default {
		name: 'notification-view-container',
		components: {xPage, Card},
		computed: {
			...mapState(['notification']),
			notificationId () {
				return this.$route.params.id
			},
            notificationData () {
				return this.notification.notificationDetails.data
            }
		},
        watch: {
			notificationData(newNotificationData) {
				if (!newNotificationData.seen) {
					this.updateNotificationsSeen([ this.notificationId ])
                }
            }
        },
		methods: {
			...mapActions({fetchNotification: FETCH_NOTIFICATION, updateNotificationsSeen: UPDATE_NOTIFICATIONS_SEEN })
		},
		mounted () {
			/*
			    Refresh or navigation directly to the url, will cause missing or incorrect notification controls.
			    This condition should identify the situation and re-fetch the notification
			 */
			if (!this.notificationData || !this.notificationData.uuid
                || (this.notificationData.uuid !== this.notificationId)) {
				this.fetchNotification(this.notificationId)
			} else if (!this.notificationData.seen) {
				this.updateNotificationsSeen([ this.notificationId ])
			}
		}
	}
</script>

<style lang="scss">

</style>