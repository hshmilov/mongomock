<template>
    <x-dropdown size="lg" align="right" :align-space="-4" :arrow="false" class="notification-peek" ref="notifications"
                @click="clearNotifications">
        <div slot="trigger">
            <svg-icon name="navigation/notifications" :original="true" height="20" />
            <div class="badge" v-if="notificationUnseenCount">{{ notificationUnseenCount }}</div>
        </div>
        <div slot="content">
            <h5 class="mb-8">Notifications</h5>
            <div v-for="notification in notificationAggregatedList"
                 @click="navigateNotification(notification.uuid)"
                 class="notification" v-bind:class="{ bold: !notification.seen }">
                <div class="status">
                    <svg-icon :name="`symbol/${notification.severity}`" :original="true" height="16"/>
                </div>
                <div class="content">
                    <div class="d-flex">
                        <div class="notification-title">{{ notification.title }}</div>
                        <div v-if="notification.count" class="c-grey-3">({{notification.count}})</div>
                    </div>
                    <div class="c-grey-4">{{ relativeDate(notification.date_fetched) }}</div>
                </div>
                <div><!-- Place for Delete --></div>
            </div>
            <div v-if="!notificationAggregatedList.length" class="t-center">
                <svg-icon name="symbol/success" :original="true" height="20px"></svg-icon>
            </div>
            <div @click="navigateNotifications" class="x-btn link">View All</div>
        </div>
    </x-dropdown>
</template>

<script>
    import xDropdown from '../../components/popover/Dropdown.vue'

    import { mapState, mapActions } from 'vuex'
	import {
    	FETCH_NOTIFICATIONS_UNSEEN_COUNT, FETCH_AGGREGATE_NOTIFICATIONS, UPDATE_NOTIFICATIONS_SEEN, FETCH_NOTIFICATION
	} from '../../store/modules/notifications'

	export default {
		name: 'notification-peek-container',
        components: { xDropdown },
        computed: {
            ...mapState({
                notificationUnseenCount(state) {
                	return state.notifications.unseenCount.data
                },
                notificationAggregatedList(state) {
                	return state.notifications.aggregatedList.data
                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Dashboard === 'ReadOnly'
                }
            })
        },
        methods: {
			...mapActions({
				fetchNotification: FETCH_NOTIFICATION,
				fetchAggregateNotifications: FETCH_AGGREGATE_NOTIFICATIONS,
				updateNotificationsSeen: UPDATE_NOTIFICATIONS_SEEN,
				fetchNotificationsUnseenCount: FETCH_NOTIFICATIONS_UNSEEN_COUNT
			}),
			relativeDate (timestamp) {
				let date = new Date(timestamp)
				let now = Date.now()
				if (now - date.getTime() < 24 * 60 * 60 * 1000) {
					return date.toLocaleTimeString()
				} else if (now - date.getTime() < 48 * 60 * 60 * 1000) {
					return 'Yesterday'
				}
				return date.toLocaleDateString()
			},
			navigateNotification (notificationId) {
				this.fetchNotification(notificationId)
				this.$refs.notifications.close()
				this.$router.push({path: `/notification/${notificationId}`})
			},
			clearNotifications() {
			    if (this.isReadOnly) return
				this.updateNotificationsSeen([])
			},
			navigateNotifications() {
				this.$refs.notifications.close()
				this.$router.push({name: 'Notifications' })
			}
        },
        created() {
			const loadNotifications = () => {
				Promise.all([this.fetchAggregateNotifications(), this.fetchNotificationsUnseenCount({})])
                    .then(() => {
						if (this._isDestroyed) return
                    	this.timer = setTimeout(loadNotifications, 9000)
					})
            }
            loadNotifications()
        },
        beforeDestroy() {
			clearTimeout(this.timer)
        }
	}
</script>

<style lang="scss">
    .notification-peek {
        &.x-dropdown > .content {
            background-color: $grey-1;
            &:before {
                content: '';
                position: absolute;
                height: 6px;
                width: 6px;
                top: -3px;
                right: 12px;
                box-shadow: $popup-shadow;
                transform: rotate(45deg);
                background-color: $grey-1;
            }
            &:after {
                content: '';
                position: absolute;
                height: 8px;
                width: 12px;
                top: 0;
                right: 10px;
                background-color: $grey-1;
            }
        }
        .notification {
            background-color: $theme-white;
            display: grid;
            grid-template-columns: 40px auto 40px;
            margin: 2px -12px;
            letter-spacing: 1px;
            padding: 12px 0;
            &.bold {
                font-weight: 500;
            }
            .status {
                line-height: 30px;
                text-align: center;
            }
            .content {
                text-overflow: ellipsis;
                overflow: hidden;
                font-size: 12px;
                line-height: 16px;
                .notification-title {
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    margin-right: 4px;
                }
            }
            &:hover {
                box-shadow: 0 0 12px rgba(0, 0, 0, 0.1)
            }
        }
        .x-btn {
            text-align: right;
            margin-bottom: -8px;
        }
    }

</style>