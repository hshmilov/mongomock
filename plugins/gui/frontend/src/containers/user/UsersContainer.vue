<template>
    <x-page title="users">
        <card :title="`users (${user.dataTable.count.data})`" class="devices-list">
            <div slot="cardActions" class="card-actions">

                <!-- Dropdown for selecting fields to be presented in table, including adapter hierarchy -->
                <graded-multi-select placeholder="Add Columns" :options="coloumnSelectionFields" v-model="selectedFields"/>
            </div>
            <div slot="cardContent">
                <x-data-table module="user" :fields="tableFields" id-field="internal_axon_id"/>
            </div>
        </card>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
    import Card from '../../components/Card.vue'
    import GradedMultiSelect from '../../components/GradedMultiSelect.vue'
    import xDataTable from '../../components/tables/DataTable.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
	import { UPDATE_TABLE_VIEW } from '../../store/mutations'
    import { FETCH_USER_FIELDS } from '../../store/modules/user'
	import { FETCH_ADAPTERS, adapterStaticData } from '../../store/modules/adapter'

	export default {
		name: 'users-container',
        components: { xPage, Card, GradedMultiSelect, xDataTable },
        computed: {
            ...mapState(['user', 'adapter']),
            selectedFields: {
				get() {
					return this.user.dataTable.view.fields
				},
				set(fieldList) {
					this.updateView({module: 'user', view: {fields: fieldList}})
				}
            },
			genericFlatSchema () {
				if (!this.user.userFields.data.generic) return []
				return this.flattenSchema(this.user.userFields.data.generic)
			},
			specificFlatSchema () {
				if (!this.user.userFields.data.specific) return []
				let registeredAdapters = new Set(this.adapter.adapterList.data.map((adapter) => adapter.plugin_name.logo))

				return Object.keys(this.user.userFields.data.specific).reduce((map, pluginName) => {
					if (!registeredAdapters.has(pluginName)) return map

					let pluginFlatSchema = this.flattenSchema(this.user.userFields.data.specific[pluginName])
					if (!pluginFlatSchema.length) return map
					let title = adapterStaticData[pluginName] ? adapterStaticData[pluginName].name : pluginName
					map[title] = pluginFlatSchema
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
            ...mapMutations({updateView: UPDATE_TABLE_VIEW}),
            ...mapActions({fetchFields: FETCH_USER_FIELDS, fetchAdapters: FETCH_ADAPTERS,}),
			flattenSchema (schema, name = '') {
				/*
				    Recursion over schema to extract a flat map from field path to its schema
				 */
				if (schema.name) {
					name = name ? `${name}.${schema.name}` : schema.name
				}
				if (schema.type === 'array' && schema.items) {
					if (!Array.isArray(schema.items)) {
						let childSchema = {...schema.items}
						if (schema.items.type !== 'array') {
							if (!schema.title) return []
							return [{...schema, name}]
						}
						if (schema.title) {
							childSchema.title = childSchema.title ? `${schema.title} ${childSchema.title}` : schema.title
						}
						return this.flattenSchema(childSchema, name)
					}
					let children = []
					schema.items.forEach((item) => {
						children = children.concat(this.flattenSchema({...item}, name))
					})
					return children
				}
				if (schema.type === 'object' && schema.properties) {
					let children = []
					Object.keys(schema.properties).forEach((key) => {
						children = children.concat(this.flattenSchema({...schema.properties[key], name: key}, name))
					})
					return children
				}
				if (!schema.title) return []
				return [{...schema, name}]
			}
        },
        created() {
			this.fetchAdapters()
            this.fetchFields()
        }
	}
</script>

<style lang="scss">

</style>