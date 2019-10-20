<template>
    <x-page :breadcrumbs="[
    	{ title: 'devices', path: { name: 'Devices'}},
    	{ title: deviceName }
    ]">
        <x-entity-view module="devices" :read-only="isReadOnly"/>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xEntityView from '../networks/entities/view/Layout.vue'

    import { mapState, mapActions } from 'vuex'
    import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../store/modules/onboarding';
    import { EXAMINE_DEVICE } from '../../constants/getting-started'

    export default {
        name: 'x-device',
        components: {xPage, xEntityView},
        mounted() {
            this.milestoneCompleted({ milestoneName: EXAMINE_DEVICE })
        },
        methods: {
            ...mapActions({milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION})
        },
        computed: {
            ...mapState({
                deviceName(state) {
                    let current = state.devices.current.data.basic
                    if (!current) return ''

                    let name = current['specific_data.data.hostname']
                    if (!name || !name.length) {
                        name = current['specific_data.data.name']
                    }
                    if (!name || !name.length) {
                        name = current['specific_data.data.pretty_id']
                    }
                    if (Array.isArray(name) && name.length) {
                        return name[0]
                    } else if (!Array.isArray(name)) {
                        return name
                    }

                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Devices === 'ReadOnly'
                }
            })
        }
    }
</script>

<style lang="scss">

</style>