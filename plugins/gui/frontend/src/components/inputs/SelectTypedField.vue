<template>
    <div class="x-select-typed-field">
        <x-select-symbol :options="fields" v-model="fieldType" @input="updateAutoField" :class="{'no-text': hideText}" />
        <x-select :options="currentFields" :value="value" @input="$emit('input', $event)" placeholder="field..."
                  :searchable="true" class="field-select" :id="id" />
    </div>
</template>

<script>
    import xSelectSymbol from './SelectSymbol.vue'
    import xSelect from './Select.vue'

	export default {
		name: 'select-typed-field',
        components: { xSelectSymbol, xSelect },
        props: { fields: { required: true }, value: {}, id: {}, hideText: { default: true } },
        computed: {
			currentFields() {
				if (!this.fields || !this.fields.length) return []
				if (!this.fieldType) return this.fields[0].fields
				return this.fields.filter(item => item.name === this.fieldType)[0].fields
			}
        },
        data() {
			return {
				fieldType: 'axonius'
            }
        },
        watch: {
			value(newValue, oldValue) {
                if (newValue && newValue !== oldValue) {
                	this.updateFieldSpace()
                }
            },
			currentFields(newCurrenFields) {
				if (!this.value) return
				if (!newCurrenFields.filter(field => field.name === this.value).length) {
					this.$emit('input', '')
				}
			}
        },
        methods: {
			updateFieldSpace() {
				let fieldSpaceMatch = /adapters_data\.(\w+_adapter)\./.exec(this.value)
				if (fieldSpaceMatch && fieldSpaceMatch.length > 1) {
					this.fieldType = fieldSpaceMatch[1]
				} else {
					this.fieldType = 'axonius'
				}
			},
            updateAutoField() {
				if (!this.value && this.fieldType !== '' && this.fieldType !== 'axonius') {
					this.$emit('input', `adapters_data.${this.fieldType}.id`)
                }
            }
        },
        created() {
			if (this.value) {
				this.updateFieldSpace()
                this.$emit('input', this.value)
            }
        }
	}
</script>

<style lang="scss">
    .x-select-typed-field {
        display: flex;
        width: 100%;
        .x-select-symbol {
            border-bottom-right-radius: 0;
            border-top-right-radius: 0;
            &.no-text .x-select-trigger .logo-text {
                display: none;
            }
        }
        .field-select {
            flex: 1 0 auto;
            margin-left: -2px;
            border-bottom-left-radius: 0;
            border-top-left-radius: 0;
            width: 180px;
        }
    }
</style>