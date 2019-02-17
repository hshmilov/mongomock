<template>
    <div class="x-action-group">
        <template v-if="isSuccessive">
            <svg-icon :name="`symbol/${condition}`" :original="true" height="20px" class="condition"></svg-icon>
            <div class="connection"></div>
        </template>
        <transition-group name="list" tag="div" class="group-items">
            <x-text-box v-if="readOnly" key="new" v-bind="{id, text, selected: anySelected, removable: false, clickable: false}" />
            <x-action v-else key="new" v-bind="{id, condition, selected: isSelected(items.length)}"
                      @click="selectAction(items.length)" class="items-new" />
            <x-action v-for="(data, i) in items" :key="data.name" v-bind="processAction(data, i)"
                      @click="selectAction(i)" @remove="removeAction(i)" />
        </transition-group>
    </div>
</template>

<script>
    import xTextBox from '../../axons/layout/TextBox.vue'
    import xAction from './Action.vue'

    export default {
        name: 'x-action-group',
        components: {
            xTextBox, xAction
        },
        props: {
            id: String,
            items: Array,
            condition: String,
            selected: Number,
            readOnly: Boolean
        },
        computed: {
            isSuccessive() {
                return this.condition !== 'main'
            },
            text() {
                return `${this.condition} actions ...`
            },
            anySelected() {
                return this.selected > -1 && this.selected <= this.items.length
            },
            empty() {
                return !this.items.length
            }
        },
        methods: {
            processAction(data, i) {
                return {
                    condition: this.condition,
                    name: data.action.action_name, title: data.name,
                    selected: this.isSelected(i), status: data.status,
                    readOnly: this.readOnly
                }
            },
            selectAction(i) {
                this.$emit('select', this.condition, i)
            },
            removeAction(i) {
                this.$emit('remove', this.condition, i)
            },
            isSelected(i) {
                return i === this.selected
            }
        }
    }
</script>

<style lang="scss">
    .x-action-group {
        display: flex;
        align-items: start;
        .condition {
            margin-left: 12px;
            margin-top: 14px;
        }
        .connection {
            height: 2px;
            background-color: $grey-4;
            width: 12px;
            margin-top: 24px;
        }
        .group-items {
            display: grid;
            grid-auto-rows: 48px;
            grid-gap: 8px 0;
            z-index: 0;
            .items-new {
                z-index: 1;
            }
            .list-enter-active, .list-leave-active {
                transition: all .4s;
            }
            .list-enter, .list-leave-to {
                opacity: 0;
                transform: translateY(-60px);
                z-index: -1;
            }
        }
    }
</style>