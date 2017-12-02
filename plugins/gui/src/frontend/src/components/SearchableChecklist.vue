<template>
    <div class="checklist" @keyup.enter="$emit('submit')">
        <div v-if="title" class="title-sm">{{ title }}</div>
        <search-input v-if="hasSearch" v-model="searchValue" ref="searchInput"></search-input>
        <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
            <div class="checklist-list">
                <checkbox v-for="item, index in requestedItems" :key="index" :label="prepareLabel(item.name)"
                          v-model="itemSelection[item.path]" @change="updateSelected"></checkbox>
                <checkbox v-if="producesNew && searchValue && isNew(searchValue)" :label="`${searchValue} (New tag)`" class="checklist-new"
                          v-model="searchValueSelected" @change="createSelected"></checkbox>
            </div>
        </vue-scrollbar>
        <div v-if="explicitSave" class="checklist-actions">
            <div><a @click="handleSave" class="link">Save</a></div>
        </div>
    </div>
</template>

<script>
    import VueScrollbar from 'vue2-scrollbar'
    import SearchInput from './SearchInput.vue'
    import Checkbox from './Checkbox.vue'

    export default {
        name: 'searchable-checklist',
        components: { VueScrollbar, SearchInput, Checkbox },
        props: [ 'title', 'hasSearch', 'producesNew', 'items', 'value', 'explicitSave', 'onDone' ],
        computed: {
            requestedItems() {
                let items = this.items.filter((item) => {
                    if (this.searchValue === '') { return true }
                    return item.name.toLowerCase().includes(this.searchValue.toLowerCase())
                })
                this.createdItems.forEach((item) => {
                	items.push({name: item, path: item})
                })
                return items
            },
            totalItemPaths() {
            	return this.items.map((item) => {
            		return item.path
                })
            }
        },
        data() {
            return {
                searchValue: '',
                searchValueSelected: false,
                itemSelection: this.value.reduce(function(map, input) {
                    map[input] = true
                    return map
                }, {}),
                createdItems: []
            }
        },
        watch: {
        	value: function(newValue) {
        		if (!newValue || !newValue.length) { this.itemSelection = {} }
        		this.itemSelection = newValue.reduce(function(map, input) {
					map[input] = true
					return map
				}, {})
            },
            searchValue: function(newSearchValue, oldSearchValue) {
        		if (this.itemSelection[oldSearchValue]) {
					this.createdItems.push(oldSearchValue)
					this.searchValueSelected = false
                }
            }
        },
        methods: {
        	prepareLabel(label) {
        		if (this.createdItems.indexOf(label) === -1) { return label }
        		return `${label} (New tag)`
            },
            isNew(item) {
        		return (this.totalItemPaths.indexOf(item) === -1) && (this.createdItems.indexOf(item) === -1)
            },
            updateSelected() {
                if (this.explicitSave) {
                	/*
                	    In the case of explicit save, the 2-way binding is not implemented.
                	    This means changes are not automatically reported to parent component,
                	    but only upon user clicking save
                	 */
            		return
                }
                let selectedItems = Object.keys(this.itemSelection).filter((id) => {
                    return this.itemSelection[id]
                })
                this.$emit('input', selectedItems)
            },
            createSelected() {
        		/*
        		    If component produces new items, one is always created from current search value.
        		    Once user selects it, it is added as an actual item, so it remains after search value is changed
                 */
            	if (this.searchValueSelected) {
					this.itemSelection[this.searchValue] = true
				}
            },
            handleSave() {
        		/*
        		    The save event is sent from this component along with an object containing two lists.
        		    The one holds items that were added to the originally selected (both new and existing).
        		    The other holds items that were removed from the originally selected.
        		 */
        		let changes = { added: [], removed: [] }
                Object.keys(this.itemSelection).forEach((item) => {
        			if (!this.itemSelection[item] && this.value.indexOf(item) > -1) {
        				changes.removed.push(item)
                    }
					if (this.itemSelection[item] && this.value.indexOf(item) === -1) {
						changes.added.push(item)
					}
                })
				this.$emit('save', changes)
                /*
                    Feedback for the save operation can be passed in the form of a method named onDone
                 */
                if (this.onDone !== undefined) {
					this.onDone(true, 'Tags Saved', 1000)
                }
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .checklist {
        .scrollbar-container {
            max-height: 240px;
            .checklist-list {
                height: 100%;
            }
            .vue-scrollbar__scrollbar-vertical {
                left: auto;
                right: 0;
            }
        }
        .checklist-actions {
            padding-top: 16px;
            margin-top: 16px;
            border-top: 1px solid $border-color;
            a {
                transition: text-shadow 0.3s ease;
                &:hover {
                    color: $color-theme-light;
                }
            }
        }
    }
</style>