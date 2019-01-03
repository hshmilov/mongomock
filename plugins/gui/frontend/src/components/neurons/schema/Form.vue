<template>
    <form class="x-form" @keyup.enter.stop="$emit('submit')">
        <x-array-edit v-model="data" :schema="schema" :api-upload="apiUpload" :read-only="readOnly"
                      @input="$emit('input', data)" @validate="onValidate"/>
        <div class="error">
            <template v-if="error">{{error}}</template>
            <template v-else-if="validity.error">{{ validity.error }}</template>
            <template v-else>&nbsp;</template>
        </div>
    </form>
</template>

<script>
    import xArrayEdit from './types/array/ArrayEdit.vue'

    /*
        Dynamically built form, according to given schema.
        Hitting the 'Enter' key from any field in the form, sends 'submit' event.
        Form elements are composed by an editable array. Therefore, schema is expected to be of type array.
        'input' event is captured and bubbled, with current data, to implement v-model.
        'validate' event is emitted with the value true if no invalid field was found and false otherwise.
     */
    export default {
        name: 'x-form',
        components: {xArrayEdit},
        props: ['value', 'schema', 'error', 'apiUpload', 'readOnly'],
        data() {
            return {
                data: {...this.value},
                validity: {
                    fields: [], error: ''
                }
            }
        },
        methods: {
            onValidate(field) {
                /*
                    field: {
                        name: <string>, valid: <boolean>, error: <string>
                    }

                    The field is added to the validity fields list, if it is invalid. Otherwise, removed.
                    The field's error, if exists, is set as the current error. Otherwise, next found error is set.

                    A field can be invalid but not have an error in cases where the user should not be able
                    to continue but also did not yet make a mistake.
                 */
                this.validity.fields = this.validity.fields.filter(x => x.name !== field.name)
                if (!field.valid) {
                    this.validity.fields.push(field)
                }
                if (field.error) {
                    this.validity.error = field.error
                } else {
                    let nextInvalidField = this.validity.fields.find(x => x.error)
                    this.validity.error = nextInvalidField ? nextInvalidField.error : ''
                }
                this.$emit('validate', this.validity.fields.length === 0)
            }
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
                this.data = {...newValue}
            }
        }
    }
</script>

<style lang="scss">
    .x-form {
        font-size: 14px;

        .array {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-gap: 12px 24px;

            .object {
                width: 100%;

                input, select {
                    width: 100%;
                    border: 1px solid $grey-2;

                    &.error-border {
                        border-color: $indicator-error;
                    }
                }

                .error-border {
                    border: 1px solid $indicator-error;
                }
            }
        }

        .error {
            color: $indicator-error;
            margin-top: 12px;
        }
    }
</style>