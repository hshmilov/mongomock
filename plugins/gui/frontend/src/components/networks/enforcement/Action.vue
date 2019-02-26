<template>
    <div class="x-action" @click="$emit('click')" :class="{[status]: status}">
        <x-text-box v-bind="{id, text, selected, removable}" @remove="onRemove">
            <template slot="logo">
                <img v-if="name" :src="require(`Logos/actions/${name}.png`)" class="md-image logo" />
                <div v-else class="logo placeholder">+</div>
            </template>
        </x-text-box>
    </div>
</template>

<script>
    import xTextBox from '../../axons/layout/TextBox.vue'
    import xButton from '../../axons/inputs/Button.vue'

    export default {
        name: 'x-action',
        components: {
            xTextBox, xButton
        },
        props: {
            id: String,
            name: String,
            title: String,
            condition: String,
            readOnly: Boolean,
            selected: Boolean,
            status: String
        },
        computed: {
            text() {
                if (this.title) return this.title

                return `${this.condition} actions ...`
            },
            removable() {
                return !this.readOnly && Boolean(this.title)
            }
        },
        methods: {
            onRemove() {
                this.$emit('remove')
            }
        }
    }
</script>

<style lang="scss">
    .x-action {
        display: flex;
        align-items: center;
        position: relative;
        .logo {
            height: 48px;
            &.placeholder {
                background-color: rgba($theme-orange, 0.2);
                min-width: 48px;
                border-radius: 50%;
                line-height: 48px;
                text-align: center;
                font-size: 36px;
            }
        }
        &.success .x-text-box {
            background-color: rgba($indicator-success, 0.4);
            &:hover, &.selected {
                background-color: rgba($indicator-success, 0.6);
            }
        }
        &.warning .x-text-box {
            background-color: rgba($indicator-warning, 0.4);
            &:hover, &.selected {
                background-color: rgba($indicator-warning, 0.6);
            }
        }
        &.error .x-text-box {
            background-color: rgba($indicator-error, 0.4);
            &:hover, &.selected {
                background-color: rgba($indicator-error, 0.6);
            }
        }
        .status {
            margin-left: 8px;
        }
    }
</style>