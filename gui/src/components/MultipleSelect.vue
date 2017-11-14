<template>
    <dropdown-menu animateClass="scale-up right" class="multiple-select">
        <image-list slot="dropdownTrigger" :data="selectedItems" :limit="2"></image-list>
        <searchable-checklist slot="dropdownContent" :title="title" :items="items" v-model="selectedItems"
                              @input="updateSelected()"></searchable-checklist>
    </dropdown-menu>
</template>

<script>
    import DropdownMenu from './DropdownMenu.vue'
    import SearchableChecklist from './SearchableChecklist.vue'
    import ImageList from './ImageList.vue'
    import './icons/fields'

    export default {
        name: 'multiple-select',
        components: { DropdownMenu, SearchableChecklist, ImageList },
        props: [ 'title', 'iconPath', 'items', 'value' ],
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
    @import '../assets/scss/config';

    .multiple-select {
        .dropdown-toggle {
            height: 30px;
        }
        .svg-icon {
            .svg-stroke {
                stroke: $color-title
            }
            .svg-fill {
                fill: $color-title
            }
        }
    }
</style>