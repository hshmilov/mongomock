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
    import xEntityView from '../networks/entities/View.vue'

    import {mapState} from 'vuex'

    export default {
        name: 'x-device',
        components: {xPage, xEntityView},
        computed: {
            ...mapState({
                deviceName(state) {
                    let current = state.devices.current.data
                    if (!current || !current.generic) return ''

                    let name = current.generic.basic['specific_data.data.hostname']
                    if (!name || !name.length) {
                        name = current.generic.basic['specific_data.data.name']
                    }
                    if (!name || !name.length) {
                        name = current.generic.basic['specific_data.data.pretty_id']
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