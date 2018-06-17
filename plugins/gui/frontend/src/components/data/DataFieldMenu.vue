<template>
    <div class="x-data-field-menu">
        <div @click="isActive = true">Edit Columns</div>
        <modal v-if="isActive" @close="isActive = false">
            <template slot="body">
                <div class="x-field-menu-filter">
                    <x-select-symbol :options="schema" v-model="fieldSpace" :tabindex="1" />
                    <search-input v-model="searchValue" :tabindex="2" />
                </div>
                <x-checkbox-list :items="currentFields" v-model="selectedFields"/>
            </template>
            <template slot="footer">
                <a class="x-btn" :tabindex="3" @click="isActive = false">Done</a>
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
    import { GET_DATA_FIELD_LIST_TYPED } from '../../store/getters'
	import { UPDATE_DATA_VIEW } from '../../store/mutations'
    import { FETCH_DATA_FIELDS } from '../../store/actions'

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
				getDataFieldsListTyped: [ GET_DATA_FIELD_LIST_TYPED ]
            }),
            schema() {
				return this.getDataFieldsListTyped(this.module)
            },
			selectedFields: {
				get() {
					return this.view.fields
				},
				set(fields) {
					this.updateView({ module: this.module, view: {
                        fields, page: -1
                    }})
				}
			},
			currentFields() {
				if (!this.schema || !this.schema.length) return []
				if (!this.fieldSpace) return this.schema[0].fields
				return this.schema.filter(item => item.name === this.fieldSpace)[0].fields.filter((field) => {
					return field.title.toLowerCase().includes(this.searchValue.toLowerCase())
                })
			}
        },
        data() {
			return {
				isActive: false,
                fieldSpace: 'axonius',
                searchValue: ''
            }
        },
        methods: {
            ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
            ...mapActions({ fetchFields: FETCH_DATA_FIELDS })
        },
        created() {
			this.fetchFields({ module: this.module })
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
        .x-select-symbol {
            flex-basis: 25%;
            margin-right: 12px;
        }
        .search-input {
            flex-basis: 25%;
        }
        .x-field-menu-filter {
            display: flex;
        }
        .x-checkbox {
            flex-basis: 25%;
            .x-checkbox-container {
                vertical-align: top;
            }
            .x-checkbox-label {
                width: calc(100% - 30px);
            }
        }
    }
</style>