<template>
    <input v-if="inputType" :id="schema.name" :type="inputType" v-model="processedData" :class="{'error-border': error}"
       @input="input" @focusout.stop="focusout" :disabled="readOnly" />
    <!-- Date Picker -->
    <x-date-edit v-else-if="isDate" v-model="data" @input="input" :read-only="readOnly" :clearable="false" :minimal="true" />
    <!-- Select from enum values -->
    <x-select v-else-if="enumOptions" :options="enumOptions" v-model="data" placeholder="value..." :searchable="true"
              @input="input" @focusout.stop="validate" :class="{'error-border': error}" :read-only="readOnly" />
</template>

<script>
	import PrimitiveMixin from '../primitive.js'
    import xSelect from '../../inputs/Select.vue'
    import xDateEdit from './DateEdit.vue'

	export default {
		name: 'x-string-edit',
        mixins: [PrimitiveMixin],
        components: { xSelect, xDateEdit },
        data() {
            return {
                data: '',
                valid: true,
                error: ''
            }
        },
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
                return this.data
            }
        }
	}
</script>

<style lang="scss">
</style>