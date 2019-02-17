<template>
    <md-field v-if="readOnly">
        <md-input type="text" disabled />
    </md-field>
    <div v-else class="x-date-edit" :class="{labeled: label}">
        <md-datepicker :value="value" @input="onInput" :md-disabled-dates="isDisabledHandler" :md-immediately="true"
                       :md-debounce="500" :class="{'no-icon': minimal, 'no-clear': !clearable}" ref="date">
            <label v-if="label">{{ label }}</label>
        </md-datepicker>
        <x-button link @click="onClear" v-if="value && clearable">X</x-button>
    </div>
</template>

<script>
    import xButton from '../../../../axons/inputs/Button.vue'

    export default {
        name: 'x-date-edit',
        components: {
            xButton
        },
        props: {
            value: {
                type: [String, Date],
                default: ''
            },
            readOnly: {
                type: Boolean, default: false
            },
            clearable: {
                type: Boolean, default: true
            },
            minimal: {
                type: Boolean, default: false
            },
            isDisabledHandler: {
                type: Function
            },
            label: {
                type: String
            }
        },
        watch: {
            value(newValue) {
                if (!newValue) {
                    this.onClear()
                }
            }
        },
        methods: {
            onInput(selectedDate) {
                if (selectedDate && typeof this.value === 'string' && typeof selectedDate !== 'string') {
                    selectedDate.setMinutes(selectedDate.getMinutes() - selectedDate.getTimezoneOffset())
                    selectedDate = selectedDate.toISOString().substring(0, 10)
                }
                this.$emit('input', selectedDate)
            },
            onClear() {
                this.$refs.date.modelDate = ''
                if (typeof this.value === 'string') {
                    this.$emit('input', '')
                } else {
                    this.$emit('input', null)
                }
                this.$emit('clear')
            }
        }
    }
</script>

<style lang="scss">
    .x-date-edit {
        display: flex;
        .md-datepicker.md-clearable {
            .md-input-action {
                visibility: hidden;
            }
        }
        &:not(.labeled) .md-datepicker.md-field {
            width: auto;
            padding-top: 0;
            min-height: auto;
            margin-bottom: 0;
        }
        .x-button.link {
            margin-left: -32px;
            margin-bottom: -4px;
            z-index: 100;
        }
    }
</style>