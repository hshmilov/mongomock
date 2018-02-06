<template>
    <form class="schema-form" @keyup.enter.stop="emitFocus(); $emit('submit')" @focusout="emitFocus">
        <x-array-edit v-model="data" :schema="schema" :validator="eventBus" @input="$emit('input', data)"></x-array-edit>
    </form>
</template>

<script>
	import Vue from 'vue'
    import xArrayEdit from '../controls/array/ArrayEdit.vue'

    /*
        Dynamically built form, according to given schema.
        Hitting the 'Enter' key from any field in the form, sends 'submit' event.
        Form elements are composed by an editable array. Therefore, schema is expected to be of type array (can be tuple).
        Event bus is passed as a validator, for 'validate' events of descendants, to be bubbled to parent.
        'input' event is captured and bubbled, with current data, to implement v-model.
     */
	export default {
		name: 'x-schema-form',
        components: {xArrayEdit},
        props: ['value', 'schema', 'onSubmit'],
        data() {
			return {
                data: { ...this.value },
                eventBus: new Vue()
            }
        },
        methods: {
			emitFocus() {
				this.eventBus.$emit('focusout')
            }
        },
        created() {
			if (!Object.keys(this.data).length) {
                this.schema.items.forEach((item) => {
                	this.data[item.name] = undefined
                })
            }
            this.eventBus.$on('validate', (valid) => this.$emit('validate', valid))
        }
	}
</script>

<style lang="scss">
    .schema-form {
        font-size: 14px;
        .array {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            .object {
                width: 240px;
                input, select {
                    width: 100%;
                }
            }
        }
    }
</style>