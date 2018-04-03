export default {
	template:'<div v-if="enumOptions">\n' +
	'    <!-- Select from finite set of possible values -->\n' +
	'    <x-select :options="enumOptions" placeholder="value..." :class="{\'invalid\': !valid}" v-model="data" @input="input" @focusout.stop="validate"/>\n' +
	'</div>\n' +
	'<input v-else :id="schema.name" type="number" v-model="data" :class="{\'invalid\': !valid}"\n' +
	'       @focusout.stop="validate" @input="input"/>'
}