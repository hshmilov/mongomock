<template>
    <x-page :breadcrumbs="[
    	{ title: 'devices', path: { name: 'Devices'}},
    	{ title: deviceName }
    ]">
        <x-data-entity module="devices" :read-only="isReadOnly" />
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
    import xDataEntity from '../../components/data/DataEntity.vue'

	import { mapState } from 'vuex'

	export default {
		name: 'device-config-container',
		components: { xPage, xDataEntity },
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
                    if (!state.auth.data || !state.auth.data.permissions) return true
                    return state.auth.data.permissions.Devices === 'ReadOnly'
                }
            })
		}
	}
</script>

<style lang="scss">

</style>