<template>
        <input v-if="inputType" :id="schema.name" :type="inputType" v-model="processedData" :class="{'error-border': error}"
           @input="input" @focusout.stop="focusout"/>
        <!-- Date Picker -->
    <x-date-edit v-else-if="schema.format === 'date-time'" v-model="data" @input="input" />
    <!-- Select from enum values -->
    <x-select v-else-if="enumOptions" :options="enumOptions" v-model="data" placeholder="value..."
              @input="input" @focusout.stop="validate" :class="{'error-border': error}" />
</template>

<script>
	import PrimitiveMixin from '../primitive.js'
    import xDateEdit from './DateEdit.vue'
    import xSelect from '../../inputs/Select.vue'

	export default {
		name: 'x-string-edit',
        mixins: [PrimitiveMixin],
        components: { xDateEdit, xSelect },
        computed: {
		    processedData: {
				get() {
					return this.isUnchangedPassword ? "********" : this.data
                },
                set(new_val) {
                    this.data = new_val
                }
            },
		    isUnchangedPassword() {
		        return this.inputType == 'password' && this.data && this.data[0] == 'unchanged'
            },
            inputType() {
				if (this.schema.format && this.schema.format === 'password') {
					return 'password'
                } else if ((this.schema.format && this.schema.format === 'date-time') || this.schema.enum) {
					return ''
                }
                return 'text'
            }
        },
	}
</script>

<style lang="scss">

</style>