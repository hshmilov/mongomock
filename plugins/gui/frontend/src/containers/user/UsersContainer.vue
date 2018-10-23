<template>
    <x-page title="users">
        <x-data-entities-table module="users" @error="errorMessage = $event" />
        <x-toast v-if="errorMessage" :message="errorMessage" @done="removeErrorMessage" />
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xDataEntitiesTable from '../../components/data/DataEntitiesTable.vue'
    import xToast from '../../components/popover/Toast.vue'

	export default {
		name: 'users-container',
        components: { xPage, xDataEntitiesTable, xToast },
        data() {
		    return {
		        errorMessage: ''
            }
        },
        methods: {
		    removeErrorMessage() {
		        this.errorMessage = ''
            }
        }
    }
</script>

<style lang="scss">

</style>