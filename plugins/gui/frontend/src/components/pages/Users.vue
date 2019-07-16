<template>
    <x-page title="users">
        <x-table module="users" />
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../networks/entities/Table.vue'
    import xToast from '../axons/popover/Toast.vue'

    export default {
        name: 'x-users',
        components: {xPage, xTable}
    }
</script>

<style lang="scss">

</style>