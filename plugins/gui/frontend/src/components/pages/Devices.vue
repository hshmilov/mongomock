<template>
    <x-page title="devices">
        <x-table module="devices"/>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../networks/entities/Table.vue'

    import {mapState, mapMutations} from 'vuex'

    export default {
        name: 'x-devices',
        components: {xPage, xTable},
    }
</script>


<style lang="scss">
</style>