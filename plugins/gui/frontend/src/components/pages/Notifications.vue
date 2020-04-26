<template>
    <x-page title="notifications">
        <x-table
          module="notifications"
          endpoint="dashboard/notifications"
          title="Notifications"
          :fields="fields"
          :on-click-row="navigateNotification"
          ref="table"
        />
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
            ...mapState(['notification']),
          fields() {
              return [
                { name: 'severity', title: 'Severity', type: 'string', format: 'icon' },
                { name: 'date_fetched', title: 'Date Time', type: 'string', format: 'date-time' },
                { name: 'plugin_name', title: 'Source', type: 'string' },
                { name: 'title', title: 'Title', type: 'string' },
              ]
          }
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
