<template>
    <div class="checklist">
        <div v-if="title" class="title-sm">{{ title }}</div>
        <search-input v-if="hasSearch" v-model="searchValue"></search-input>
        <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
            <div class="checklist-list">
                <checkbox v-for="item in requestedItems" :key="item.path" :label="item.name"
                          v-model="itemSelection[item.path]" @change="updateSelected()"></checkbox>
                <checkbox v-if="producesNew && searchValue" :label="`${searchValue} (New tag)`" class="checklist-new"
                          v-model="itemSelection[searchValue]" @change="updateSelected()"></checkbox>
            </div>
        </vue-scrollbar>
        <div v-if="explicitSave" class="checklist-actions">
            <div><a @click="handleSave">Save</a></div>
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
                let _this = this
                return this.items.filter(function(item) {
                    if (_this.searchValue === '') { return true }
                    return item.name.toLowerCase().includes(_this.searchValue.toLowerCase())
                })
            }
        },
        data() {
            return {
                searchValue: '',
                itemSelection: this.value.reduce(function(map, input) {
                    map[input] = true
                    return map
                }, {})
            }
        },
        watch: {
        	value: function(newValue) {
        		if (!Object.keys(newValue).length) { return }
        		this.itemSelection = newValue.reduce(function(map, input) {
					map[input] = true
					return map
				}, {})
            }
        },
        methods: {
            updateSelected() {
                let _this = this
                let selectedItems = Object.keys(this.itemSelection).filter(function(id) {
                    return _this.itemSelection[id]
                })
                this.$emit('input', selectedItems)
            },
            handleSave() {
				this.$emit('save')
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
                    color: $color-theme;
                }
            }
        }
    }
</style>