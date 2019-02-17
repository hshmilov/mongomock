<template>
    <x-select v-bind="{options, value, placeholder, id, readOnly, searchable: true, size: 'sm'}" @input="selectOption"
              class="x-select-symbol" :class="{minimal}">
        <template slot-scope="{ option }">
            <div class="x-type-img">
                <img v-if="type === 'img'" :src="require(`Logos/adapters/${option.name}.png`)"/>
                <svg-icon v-else-if="type === 'icon'" :name="`navigation/${option.name}`" :original="true" width="30"/>
            </div>
            <div class="logo-text">{{option.title}}</div>
        </template>
    </x-select>
</template>

<script>
    import xSelect from '../../axons/inputs/Select.vue'

    export default {
        name: 'x-select-symbol',
        components: {xSelect},
        props: {
            options: {required: true},
            value: {},
            type: {default: 'img'},
            placeholder: {},
            id: {},
            minimal: Boolean,
            readOnly: Boolean
        },
        methods: {
            selectOption(option) {
                this.$emit('input', option)
            }
        }
    }
</script>

<style lang="scss">
    .x-select-symbol {
        .x-type-img {
            width: 30px;
            line-height: 14px;
            text-align: center;
            display: inline-block;
            vertical-align: middle;

            img {
                max-width: 30px;
                max-height: 24px;
            }

            .svg-icon {
                .svg-stroke {
                    stroke: $grey-4;
                }

                .svg-fill {
                    fill: $grey-4;
                }
            }
        }

        .logo-text {
            max-width: 160px;
            margin-top: 2px;
        }
        &.minimal .x-select-trigger .logo-text {
            display: none;
        }
    }
</style>