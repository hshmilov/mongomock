export default {
	template:'<div v-if="schema.enum">\n' +
	'    <!-- Select from finite set of possible values -->\n' +
	'    <select :class="{\'invalid\': !valid}" v-model="data" @change="input" @focusout.stop="validate">\n' +
	'        <option value="" disabled hidden>VALUE...</option>\n' +
	'        <template v-for="item in schema.enum">\n' +
	'            <option v-if="item.name" :value="item.name">{{ item.value }}</option>\n' +
	'            <option v-else :value="item">{{ item }}</option>\n' +
	'        </template>\n' +
	'    </select>\n' +
	'</div>\n' +
	'<input v-else :id="schema.name" type="number" v-model="data" :class="{\'invalid\': !valid}"\n' +
	'       @focusout.stop="validate" @input="input"/>'
}