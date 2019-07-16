<template>
    <x-page title="devices">
        <x-table module="devices" @data="updateDeviceState" />
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../networks/entities/Table.vue'

    import {mapState, mapMutations} from 'vuex'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'x-devices',
        components: {xPage, xTable},
        computed: {
            ...mapState({
                tourDevices(state) {
                    return state.onboarding.tourStates.queues.devices
                }
            })
        },
        methods: {
            ...mapMutations({
              changeState: CHANGE_TOUR_STATE
            }),
            updateDeviceState(deviceId) {
                if (!this.tourDevices || !this.tourDevices.length) return
                if (this.tourDevices[0] === 'bestDevice') {
                    if (!deviceId) {
                        this.changeState({name: ''})
                    } else {
                        this.changeState({name: 'bestDevice', id: deviceId})
                    }
                } else {
                    this.changeState({name: this.tourDevices[0]})
                }
            }
        }
    }
</script>


<style lang="scss">
</style>