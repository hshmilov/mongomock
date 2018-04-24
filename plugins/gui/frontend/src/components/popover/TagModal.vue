<template>
    <feedback-modal v-model="isActive" :handle-save="saveTags" :message="`Tagged ${entities.length} ${module}s!`"
                    class="x-tag-modal">
        <search-input v-model="searchValue" ref="searchInput" tabindex="1"/>
        <x-checkbox-list :items="currentLabels" v-model="selected"/>
    </feedback-modal>
</template>

<script>
    import FeedbackModal from './FeedbackModal.vue'
	import SearchInput from '../inputs/SearchInput.vue'
    import xCheckboxList from '../inputs/CheckboxList.vue'

	import { mapState, mapGetters, mapActions } from 'vuex'
    import { GET_DATA_BY_ID } from '../../store/getters'
    import { FETCH_DATA_LABELS, ADD_DATA_LABELS, REMOVE_DATA_LABELS } from '../../store/actions'

	export default {
		name: 'x-tag-modal',
        components: { FeedbackModal, SearchInput, xCheckboxList },
        props: {module: {required: true}, entities: {required: true}, tags: {}, title: {}},
		computed: {
            ...mapState({
				labels(state) {
					return state[this.module].labels.data.sort()
				},
            }),
            ...mapGetters({getDataByID: GET_DATA_BY_ID}),
            dataByID() {
            	return this.getDataByID(this.module)
            },
            currentLabels() {
            	if (!this.searchValue) return this.labels
                let matchingLabels = this.labels.filter((label) => {
                	return label.name.toLowerCase().includes(this.searchValue.toLowerCase())
				})
                if (!matchingLabels.length || matchingLabels[0].name !== this.searchValue) {
            		matchingLabels.unshift({ name: this.searchValue, title: `${this.searchValue} (new)`})
                }
                return matchingLabels
            }
        },
        data () {
			return {
                isActive: false,
                selected: [],
                searchValue: ''
			}
		},
		watch: {
			tags (newLabels) {
				this.selected = newLabels
			}
		},
		methods: {
			...mapActions({
                fetchLabels: FETCH_DATA_LABELS, addLabels: ADD_DATA_LABELS, removeLabels: REMOVE_DATA_LABELS
			}),
            activate() {
				this.isActive = true
            },
			saveTags () {
				if (!this.selected || !this.selected.length) return
				/* Separate added and removed tags and create an uber promise returning after both are updated */
				let added = this.selected.filter((tag) => {
					return (!this.tags.includes(tag))
				})
				let removed = this.tags.filter((tag) => {
					return (!this.selected.includes(tag))
				})
				this.searchValue = ''
				return Promise.all([
					this.addLabels({module: this.module, data: {entities: this.entities, labels: added}}),
					this.removeLabels({module: this.module, data: {entities: this.entities, labels: removed}})
                ])
			},
			removeEntitiesLabels(labels) {
				this.removeLabels({module: this.module, data: {entities: this.entities, labels}})
            }
		},
        created() {
			this.fetchLabels({module: this.module})
        },
        mounted() {
            this.$refs.searchInput.focus()
        }
	}
</script>

<style lang="scss">
    .x-tag-modal {
        .search-input {
            width: 50%;
        }
        .x-checkbox {
            flex-basis: 50%;
        }
    }
</style>