<template>
    <form class="schema-form" @keyup.enter.stop="$emit('submit')">
        <x-array-edit v-model="data" :schema="schema" @input="$emit('input', data)" @validate="updateValidity" />
        <div class="error-text">
            <template v-if="error">{{error}}</template>
            <template v-else-if="invalid.length">Complete "{{invalid[0]}}" to save data</template>
            <template v-else>&nbsp;</template>
        </div>
    </form>
</template>

<script>
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
        components: { xArrayEdit },
        props: ['value', 'schema', 'error'],
        data() {
			return {
                data: { ...this.value },
				invalid: []
			}
        },
        methods: {
			updateValidity(field) {
				let invalidFields = new Set(this.invalid)
				if (field.valid) {
					invalidFields.delete(field.title)
				} else {
					invalidFields.add(field.title)
				}
				this.invalid = Array.from(invalidFields)
				this.$emit('validate', this.invalid.length === 0)
			},
        },
        created() {
			if (!Object.keys(this.data).length) {
                this.schema.items.forEach((item) => {
                	this.data[item.name] = undefined
                })
            }
        },
        watch: {
		    value(newValue) {
		        this.data = { ...newValue }
            }
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
                    border: 1px solid $grey-2;
                    &.invalid {
                        border-color: $indicator-red;
                    }
                }
            }
        }
    }
</style>