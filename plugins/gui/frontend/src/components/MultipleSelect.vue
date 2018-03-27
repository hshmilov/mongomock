<template>
    <triggerable-dropdown class="multiple-select">
        <object-list slot="dropdownTrigger" :type="type" :data="selectedItems" :limit="2"></object-list>
        <searchable-checklist slot="dropdownContent" :title="title" :items="items" v-model="selectedItems"
                              @input="updateSelected()"></searchable-checklist>
    </triggerable-dropdown>
</template>

<script>
    import TriggerableDropdown from './popover/TriggerableDropdown.vue'
    import SearchableChecklist from './SearchableChecklist.vue'
    import ObjectList from './ObjectList.vue'

    export default {
        name: 'multiple-select',
        components: { TriggerableDropdown, SearchableChecklist, ObjectList },
        props: [ 'title', 'type', 'iconPath', 'items', 'value' ],
        data() {
            return {
                selectedItems: []
            }
        },
        methods: {
            updateSelected() {
                this.$emit('input', this.selectedItems)
            }
        },
        created() {
            this.selectedItems = this.value || []
        }
    }
</script>

<style lang="scss">
    .multiple-select {
        .dropdown-toggle {
            height: 30px;
            border-radius: 4px;
            border: 1px solid rgba(0, 0, 0, 0.15);
        }
        .svg-icon {
            .svg-stroke {
                stroke: $color-text-main
            }
            .svg-fill {
                fill: $color-text-main
            }
        }
        .object-list {
            line-height: 30px;
        }
    }
</style>