<template>
    <x-page title="notifications">
        <x-table module="notifications" title="Notifications" :on-click-row="navigateNotification" ref="table"/>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../neurons/data/Table.vue'

    import {mapState, mapActions} from 'vuex'
    import {FETCH_NOTIFICATION} from '../../store/modules/notifications'

    export default {
        name: 'x-notifications',
        components: {xPage, xTable},
        computed: {
            ...mapState(['notification'])
        },
        methods: {
            ...mapActions({
                fetchNotification: FETCH_NOTIFICATION
            }),
            navigateNotification(notificationId) {
                this.fetchNotification(notificationId)
                this.$router.push({path: `/notifications/${notificationId}`})
            }
        }
    }
</script>

<style lang="scss">

</style>