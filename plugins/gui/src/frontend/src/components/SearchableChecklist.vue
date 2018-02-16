<template>
    <div class="checklist" @keyup.enter="$emit('submit')">
        <div v-if="title" class="title-sm">{{ title }}</div>
        <search-input v-if="searchable" v-model="searchValue" ref="searchInput"></search-input>
        <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
            <div class="checklist-list">
                <template v-for="item, index in filteredItems">
                    <checkbox v-if="item.name" :key="index" :label="prepareLabel(item.title)"
                              v-model="itemSelection[item.name]" @change="updateSelected"></checkbox>
                    <div v-else class="title">{{ item.title }}</div>
                </template>
                <checkbox v-if="extendable && searchValue && isNew(searchValue)" :label="`${searchValue} (New tag)`"
                          class="checklist-new" v-model="searchValueSelected" @change="createSelected"></checkbox>
            </div>
        </vue-scrollbar>
    </div>
</template>

<script>
    import VueScrollbar from 'vue2-scrollbar'
    import SearchInput from './SearchInput.vue'
    import Checkbox from './Checkbox.vue'

    export default {
        name: 'searchable-checklist',
        components: { VueScrollbar, SearchInput, Checkbox },
        props: [ 'title', 'searchable', 'extendable', 'items', 'value' ],
        computed: {
            totalItems() {
                return this.items.map((item) => {
                	if (item.name || item.title) return item
                    return { name: item, title: item }
                })
            },
            filteredItems() {
            	return this.totalItems.filter((item) => {
					if (this.searchValue === '') { return true }
					return item.title.toLowerCase().includes(this.searchValue.toLowerCase())
				})
            },
            totalItemNames() {
            	return this.items.map((item) => {
            		return item.name
                })
            }
        },
        data() {
            return {
                searchValue: '',
                searchValueSelected: false,
                itemSelection: {},
                createdItems: []
            }
        },
        watch: {
        	value: function(newValue) {
        		if (!newValue || !newValue.length) {
        			this.itemSelection = {}
        		} else {
					this.itemSelection = newValue.reduce(function(map, input) {
						map[input] = true
						return map
					}, {})
				}
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
        		return (this.totalItemNames.indexOf(item) === -1) && (this.createdItems.indexOf(item) === -1)
            },
            updateSelected() {
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
				this.updateSelected()
            }
        },
        created() {
        	if (!this.value) { return }
			this.itemSelection = this.value.reduce(function(map, input) {
				map[input] = true
				return map
			}, {})
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .checklist {
        .scrollbar-container {
            max-height: 480px;
            .checklist-list {
                height: 100%;
                .checkbox {
                    margin-top: 8px;
                    width: 100%;
                    &:first-of-type {
                        margin-top: 0;
                    }
                }
                .title {
                    font-weight: 300;
                    text-transform: uppercase;
                    margin-top: 8px;
                }
            }
            .vue-scrollbar__scrollbar-vertical {
                left: auto;
                right: 0;
            }
        }
    }
</style>