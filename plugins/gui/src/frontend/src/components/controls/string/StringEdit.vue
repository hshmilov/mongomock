<template>
    <input v-if="inputType" :id="schema.name" :type="inputType" v-model="data" :class="{'invalid': !valid}"
           @focusout.stop="handleData"/>
    <div v-else-if="schema.format === 'date-time'">
        <!-- Date Picker -->
    </div>
    <div v-else-if="schema.enum">
        <!-- Select from enum values -->
    </div>
</template>

<script>
	import PrimitiveMixin from '../primitive.js'

	export default {
		name: 'x-string-edit',
        mixins: [PrimitiveMixin],
        computed: {
			formattedData() {
				if (this.schema.format === 'date-time') {
                    let dateTime = new Date(this.data)
                    return `${dateTime.toLocaleDateString()} ${dateTime.toLocaleTimeString()}`
                }
                return this.data
            },
            inputType() {
				if (this.schema.format && this.schema.format === 'password') {
					return 'password'
                } else if (this.schema.format && this.schema.format === 'date-time') {
					return ''
                }
                return 'text'
            }
        }
	}
</script>

<style lang="scss">

</style>