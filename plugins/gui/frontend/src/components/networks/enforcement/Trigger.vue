<template>
    <div class="x-trigger" @click="$emit('click')">
        <x-text-box v-bind="{id, text, selected, removable: false}">
            <template slot="logo">
                <img v-if="title" :src="require('Logos/actions/trigger.png')" class="md-image logo" />
                <div v-else class="logo placeholder">+</div>
            </template>
        </x-text-box>
    </div>
</template>

<script>
    import xTextBox from '../../axons/layout/TextBox.vue'
    import xButton from '../../axons/inputs/Button.vue'

    export default {
        name: 'x-trigger',
        components: {
            xTextBox, xButton
        },
        props: {
            id: String,
            title: String,
            selected: Boolean
        },
        computed: {
            text() {
                if (this.title) return this.title

                return 'Trigger'
            }
        }
    }
</script>

<style lang="scss">
    .x-trigger {
        display: flex;
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
    }
</style>