<template>
    <x-page :breadcrumbs="[
    	{title: 'notifications', path: {'name': 'Notifications'}},
        {title: notifications.current.data.title}
        ]">
        <x-box>
            <div class="show-space">{{notifications.current.data.content}}</div>
        </x-box>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xBox from '../axons/layout/Box.vue'

    import {mapState, mapActions} from 'vuex'
    import {FETCH_NOTIFICATION, UPDATE_NOTIFICATIONS_SEEN} from '../../store/modules/notifications'

    export default {
        name: 'x-notification',
        components: {xPage, xBox},
        computed: {
            ...mapState({
                notifications(state) {
                    return state.notifications
                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Dashboard === 'ReadOnly'
                }
            }),
            notificationId() {
                return this.$route.params.id
            },
            notificationData() {
                return this.notifications.current.data
            }
        },
        watch: {
            notificationData(newNotificationData) {
                if (!newNotificationData.seen && !this.isReadOnly) {
                    this.updateNotificationsSeen([this.notificationId])
                }
            }
        },
        methods: {
            ...mapActions({fetchNotification: FETCH_NOTIFICATION, updateNotificationsSeen: UPDATE_NOTIFICATIONS_SEEN})
        },
        mounted() {
            /*
                Refresh or navigation directly to the url, will cause missing or incorrect notifications controls.
                This condition should identify the situation and re-fetch the notifications
             */
            if (!this.notificationData || !this.notificationData.uuid
                || (this.notificationData.uuid !== this.notificationId)) {
                this.fetchNotification(this.notificationId)
            } else if (!this.notificationData.seen && !this.isReadOnly) {
                this.updateNotificationsSeen([this.notificationId])
            }
        }
    }
</script>

<style lang="scss">

</style>