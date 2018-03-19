<template>
    <x-page title="users">
        <x-data-query module="user" :schema="coloumnSelectionFields" :selected="selectedFields"/>
        <x-data-table module="user" :fields="tableFields" id-field="internal_axon_id" title="Users">
            <template slot="tableActions">
            <!-- Dropdown for selecting fields to be presented in table, including adapter hierarchy -->
            <graded-multi-select placeholder="Add Columns" :options="coloumnSelectionFields" v-model="selectedFields"/>
            </template>
        </x-data-table>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
    import xDataQuery from '../../components/data/DataQuery.vue'
    import GradedMultiSelect from '../../components/GradedMultiSelect.vue'
    import xDataTable from '../../components/tables/DataTable.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
	import { UPDATE_DATA_VIEW } from '../../store/mutations'
    import { FETCH_DATA_FIELDS } from '../../store/actions'
	import { FETCH_ADAPTERS, adapterStaticData } from '../../store/modules/adapter'

	export default {
		name: 'users-container',
        components: { xPage, xDataQuery, GradedMultiSelect, xDataTable },
        computed: {
            ...mapState(['user', 'adapter']),
            selectedFields: {
				get() {
					return this.user.data.view.fields
				},
				set(fieldList) {
					this.updateView({module: 'user', view: {fields: fieldList}})
				}
            },
            userFields() {
            	return this.user.data.fields.data
            },
			genericFlatSchema () {
				if (!this.userFields.generic) return []
				return this.userFields.generic
			},
			specificFlatSchema () {
				if (!this.userFields.specific) return {}
				let registeredAdapters = this.adapter.adapterList.data.map((adapter) => adapter.plugin_name.logo)

				return registeredAdapters.reduce((map, name) => {
					map[name] = this.userFields.specific[name]
					return map
				}, {})
			},
			coloumnSelectionFields() {
				if (!this.genericFlatSchema.length) return []

				return [
					{
						title: 'Generic', fields: this.genericFlatSchema
					},
					...Object.keys(this.specificFlatSchema).map((title) => {
						return { title, fields: this.specificFlatSchema[title] }
					})
				]
			},
			tableFields () {
				if (!this.genericFlatSchema.length) return []
				return this.genericFlatSchema.filter((field) => {
					return !(field.type === 'array' && (Array.isArray(field.items) || field.items.type === 'array'))
				}).concat(Object.keys(this.specificFlatSchema).reduce((merged, title) => {
					if (!this.specificFlatSchema[title]) return merged
					merged = [...merged, ...this.specificFlatSchema[title].map((field) => {
						return { ...field, title: `${title} ${field.title}`}
					})]
					return merged
				}, []))
			}
        },
        data() {
			return {
			    selectedUsers: []
            }
        },
        methods: {
            ...mapMutations({updateView: UPDATE_DATA_VIEW}),
            ...mapActions({fetchFields: FETCH_DATA_FIELDS, fetchAdapters: FETCH_ADAPTERS})
        },
        created() {
			this.fetchAdapters()
            this.fetchFields({module: 'user'})
        }
	}
</script>

<style lang="scss">

</style>