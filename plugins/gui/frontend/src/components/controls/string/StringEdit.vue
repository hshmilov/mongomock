<template>
    <input v-if="inputType" :id="schema.name" :type="inputType" v-model="processedData" :class="{'error-border': error}"
       @input="input" @focusout.stop="focusout" :disabled="readOnly" />
    <!-- Date Picker -->
    <md-field v-else-if="isDate && readOnly">
        <md-input type="text" disabled />
    </md-field>
    <md-datepicker v-else-if="isDate" v-model="data" @input="input" :md-immediately="true" :md-clearable="false" class="no-clear" />
    <!-- Select from enum values -->
    <x-select v-else-if="enumOptions" :options="enumOptions" v-model="data" placeholder="value..." :searchable="true"
              @input="input" @focusout.stop="validate" :class="{'error-border': error}" :read-only="readOnly" />
</template>

<script>
	import PrimitiveMixin from '../primitive.js'
    import xSelect from '../../inputs/Select.vue'

	export default {
		name: 'x-string-edit',
        mixins: [PrimitiveMixin],
        components: { xSelect },
        computed: {
		    processedData: {
				get() {
					return this.isUnchangedPassword ? "********" : this.data
                },
                set(new_val) {
                    this.data = new_val
                }
            },
            isDate() {
		        return (this.schema.format === 'date-time' || this.schema.format === 'date')
            },
		    isUnchangedPassword() {
		        return this.inputType === 'password' && this.data && this.data[0] === 'unchanged'
            },
            inputType() {
				if (this.schema.format && this.schema.format === 'password') {
					return 'password'
                } else if (this.isDate || this.schema.enum) {
					return ''
                }
                return 'text'
            }
        },
        methods: {
		    formatData() {
                if (this.isDate) {
                    return this.data.toISOString().substring(0, 10)
                }
                return this.data
            }
        }
	}
</script>

<style lang="scss">
</style>