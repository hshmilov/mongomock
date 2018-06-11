<template>
    <input v-if="inputType" :id="schema.name" :type="inputType" v-model="data" :class="{'invalid': !valid}"
           @input="input" @focusout.stop="validate"/>
        <!-- Date Picker -->
    <x-date-edit v-else-if="schema.format === 'date-time'" v-model="data" @input="input" />
    <!-- Select from enum values -->
    <x-select v-else-if="enumOptions" :options="enumOptions" v-model="data" placeholder="value..." :class="{'invalid': !valid}"
              @input="input" @focusout.stop="validate"/>
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
            }
        }
	}
</script>

<style lang="scss">

</style>