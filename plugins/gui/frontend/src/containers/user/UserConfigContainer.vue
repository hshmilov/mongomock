<template>
    <x-page :breadcrumbs="[
    	{ title: 'users', path: { name: 'Users'}},
    	{ title: userName }
    ]">
        <x-data-entity module="users" :read-only="isReadOnly" />
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import xDataEntity from '../../components/data/DataEntity.vue'

    import { mapState } from 'vuex'

	export default {
		name: 'user-config-container',
        components: { xPage, xDataEntity },
        computed: {
            ...mapState({
                userName(state) {
                	let current = state.users.current.data
                    if (!current || !current.generic) return

                	let name = current.generic.basic['specific_data.data.username']
                    if (!name || !name.length) {
                		return this.$route.params.id
                    }
					if (Array.isArray(name) && name.length) {
						return name[0]
					} else if (!Array.isArray(name)) {
						return name
					}
                },
                isReadOnly(state) {
                    if (!state.auth.data || !state.auth.data.permissions) return true
                    return state.auth.data.permissions.Users === 'ReadOnly'
                }
            })
        }
	}
</script>

<style scoped>

</style>