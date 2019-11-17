<template>
    <x-page title="devices">
        <x-table module="devices" @row-clicked="rowClicked"/>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../networks/entities/Table.vue'
    import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../store/modules/onboarding';
    import { EXAMINE_DEVICE } from '../../constants/getting-started'
    import {mapActions} from 'vuex'

    export default {
        name: 'x-devices',
        components: {xPage, xTable},
        methods: {
            ...mapActions({milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION}),
            rowClicked() {
                this.milestoneCompleted({ milestoneName: EXAMINE_DEVICE })
            }
        }
    }
</script>


<style lang="scss">
</style>