<template>
    <div class="x-data-field-menu">
        <button @click="isActive = true" class="x-btn link">Edit Columns</button>
        <modal v-if="isActive" @close="isActive = false">
            <template slot="body">
                <div class="x-field-menu-filter">
                    <x-select-symbol :options="schema" v-model="fieldType" :tabindex="1" />
                    <search-input v-model="searchValue" :tabindex="2" />
                </div>
                <x-checkbox-list :items="currentFields" v-model="selectedFields"/>
            </template>
            <template slot="footer">
                <button class="x-btn" :tabindex="3" @click="isActive = false">Done</button>
            </template>
        </modal>
    </div>
</template>

<script>
    import Modal from '../popover/Modal.vue'
	import xSelectSymbol from '../inputs/SelectSymbol.vue'
    import SearchInput from '../inputs/SearchInput.vue'
    import xCheckboxList from '../inputs/CheckboxList.vue'
    import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { GET_DATA_FIELD_BY_PLUGIN } from '../../store/getters'
	import { UPDATE_DATA_VIEW } from '../../store/mutations'

	export default {
		name: 'x-data-field-menu',
        components: { Modal, xSelectSymbol, SearchInput, xCheckboxList },
        props: { module: { required: true }},
        computed: {
            ...mapState({
				view(state) {
					return state[this.module].view
				}
            }),
            ...mapGetters( {
				getDataFieldsByPlugin: [ GET_DATA_FIELD_BY_PLUGIN ]
            }),
            schema() {
				return this.getDataFieldsByPlugin(this.module)
            },
			selectedFields: {
				get() {
					return this.view.fields
				},
				set(fields) {
					this.updateView({ module: this.module, view: { fields }})
				}
			},
			currentFields() {
				if (!this.schema || !this.schema.length) return []
				if (!this.fieldType) return this.schema[0].fields
                let fieldSchema = this.schema.find(item => item.name === this.fieldType)
                if (!fieldSchema) return []
				return fieldSchema.fields.filter((field) => {
					return field.title.toLowerCase().includes(this.searchValue.toLowerCase())
                })
			},
            firstType() {
				if (!this.schema || !this.schema.length) return 'axonius'
				return this.schema[0].name
            }
        },
        data() {
			return {
				isActive: false,
                fieldType: '',
                searchValue: ''
            }
        },
        watch: {
			firstType(newFirstType) {
				this.fieldType = newFirstType
			}
        },
        methods: {
            ...mapMutations({ updateView: UPDATE_DATA_VIEW })
        },
        created() {
			this.fieldType = this.firstType
        }
	}
</script>

<style lang="scss">
    .x-data-field-menu {
        .modal-mask .modal-wrapper .modal-container {
            width: 80vw;
        }

        .x-select-trigger {
            color: $theme-black;
        }


        .x-field-menu-filter {
            display: flex;
            .x-select-symbol {
                margin-right: 12px;
                flex-basis: 40%;
            }
            .search-input {
                flex: 1 0 auto;
            }
        }
    }
</style>