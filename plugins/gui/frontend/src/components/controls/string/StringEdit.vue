<template>
    <input v-if="inputType" :id="schema.name" :type="inputType" v-model="data" :class="{'invalid': !valid}"
           @input="input" @focusout.stop="validate"/>
    <div v-else-if="schema.format === 'date-time'">
        <!-- Date Picker -->
        <x-date-edit v-model="data" @input="input" />
    </div>
    <div v-else-if="schema.enum">
        <!-- Select from enum values -->
        <select :class="{'invalid': !valid}" v-model="data" @change="input" @focusout.stop="validate">
            <option value="" disabled hidden>VALUE...</option>
            <template v-for="item in schema.enum">
                <option v-if="item.name" :value="item.name">{{item.title || item.name}}</option>
                <option v-else :value="item">{{item}}</option>
            </template>
        </select>
    </div>
</template>

<script>
	import PrimitiveMixin from '../primitive.js'
    import xDateEdit from './DateEdit.vue'

	export default {
		name: 'x-string-edit',
        mixins: [PrimitiveMixin],
        components: { xDateEdit },
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