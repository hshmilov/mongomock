<template>
    <div class="checklist">
        <div v-if="title" class="title-sm">{{ title }}</div>
        <div class="input-group">
            <input type="text" v-model="searchValue" class="checklist-search form-control">
            <span class="input-group-addon"><i class="icon-search"></i></span>
        </div>
        <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
            <div class="checklist-list">
                <checkbox v-for="item in requestedItems" :key="item.path"
                          :label="item.name" v-model="item.selected"
                          :clickHandler="actionOne.bind(this, item.path)"></checkbox>
            </div>
        </vue-scrollbar>
        <div class="checklist-actions">
            <slot name="checklistActions"></slot>
        </div>
    </div>
</template>

<script>
    import VueScrollbar from 'vue2-scrollbar'
    import Checkbox from './Checkbox.vue'

    export default {
        name: 'searchable-checklist',
        components: { VueScrollbar, Checkbox },
        props: ['title', 'items', 'actionOne' ],
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
                searchValue: ''
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .checklist {
        .checklist-search {
            width: 100%;
            border-radius: 4px;
            border: 1px solid $border-color;
            border-right: 0;
            margin-bottom: 12px;
            height: 30px;
        }
        .input-group {
            .input-group-addon {
                height: 30px;
                padding-right: 8px;
                padding-left: 8px;
                background-color: transparent;
                color:  $color-disabled;
            }
        }
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
            margin-top: 16px;
            border-top: 1px solid $border-color;
        }
    }
</style>