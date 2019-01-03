export default {
	template:
	'<div v-if="enumOptions">\n' +
	'    <!-- Select from finite set of possible values -->\n' +
	'    <x-select :options="enumOptions" placeholder="value..." :class="{\'error-border\': error}" v-model="data"' +
	'				@focusout.stop="focusout" @input="input" :disabled="readOnly" />\n' +
	'</div>\n' +
	'<input v-else :id="schema.name" type="number" v-model="data" :class="{\'error-border\': error}"\n' +
	'       @focusout.stop="focusout" @input="input" :disabled="readOnly" @keypress="validateNumber" />'
}