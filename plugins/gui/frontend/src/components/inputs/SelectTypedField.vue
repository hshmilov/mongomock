<template>
    <div class="x-select-typed-field">
        <x-select-symbol v-if="isTyped" :options="options" v-model="fieldType" :class="{'no-text': hideText}" />
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
        props: {
		    options: { required: true }, value: {}, id: {}, hideText: { default: true }
        },
        computed: {
		    isTyped() {
		        return this.options && this.options.length && this.options[0].fields
            },
			currentFields() {
				if (!this.isTyped) return this.options
				if (!this.fieldType) return this.options[0].fields
				return this.options.find(item => item.name === this.fieldType).fields
			},
            firstType() {
				if (!this.options || !this.options.length) return 'axonius'
				return this.options[0].name
            }
        },
        data() {
			return {
				fieldType: ''
            }
        },
        watch: {
			value(newValue, oldValue) {
                if (newValue && newValue !== oldValue) {
                	this.updateFieldType()
                } else if (!newValue) {
                	this.fieldType = 'axonius'
                }
            },
			currentFields(newCurrenFields) {
				if (!this.value) return
				if (!newCurrenFields.filter(field => field.name === this.value).length) {
					this.$emit('input', '')
				}
			},
            firstType(newFirstType) {
				this.fieldType = newFirstType
            },
            fieldType() {
                if (this.isTyped && this.fieldType !== '' && this.fieldType !== 'axonius') {
                    this.$emit('input', `adapters_data.${this.fieldType}.id`)
                }
            }
        },
        methods: {
			updateFieldType() {
				let fieldSpaceMatch = /adapters_data\.(\w+)\./.exec(this.value)
				if (fieldSpaceMatch && fieldSpaceMatch.length > 1) {
					this.fieldType = fieldSpaceMatch[1]
				} else {
					this.fieldType = 'axonius'
				}
			}
        },
        created() {
			this.fieldType = this.firstType
			if (this.value) {
				this.updateFieldType()
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