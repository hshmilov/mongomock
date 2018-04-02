<template>
    <input v-if="inputType" :id="schema.name" :type="inputType" v-model="data" :class="{'invalid': !valid}"
           @input="input" @focusout.stop="validate"/>
    <div v-else-if="schema.format === 'date-time'">
        <!-- Date Picker -->
        <x-date-edit v-model="data" @input="input" />
    </div>
    <div v-else-if="enumOptions">
        <!-- Select from enum values -->
        <x-select :options="enumOptions" v-model="data" placeholder="value..." :class="{'invalid': !valid}"
                  @input="input" @focusout.stop="validate"/>
    </div>
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
            inputType() {
				if (this.schema.format && this.schema.format === 'password') {
					return 'password'
                } else if ((this.schema.format && this.schema.format === 'date-time') || this.schema.enum) {
					return ''
                }
                return 'text'
            },
            enumOptions() {
            	if (!this.schema.enum) return undefined
                return this.schema.enum.map((item) => {
                	if (typeof item !== 'string' && item.name) return item
                    return {name: item, title: item}
                })
            }
        }
	}
</script>

<style lang="scss">

</style>