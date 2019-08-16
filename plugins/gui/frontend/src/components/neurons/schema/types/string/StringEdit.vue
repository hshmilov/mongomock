<template>
  <!-- Date Picker -->
  <x-date-edit
    v-if="isDate"
    v-model="data"
    :read-only="readOnly"
    :minimal="true"
    :clearable="clearable"
    @input="input"
  />
  <textarea v-else-if="isText" v-model="data" :maxlength="schema.limit" rows="3" @input="input"></textarea>

  <input
    v-else-if="inputType"
    :id="schema.name"
    v-model="processedData"
    :type="inputType"
    :class="{'error-border': error}"
    :disabled="readOnly || schema.readOnly"
    :placeholder="schema.placeholder"
    @input="input"
    @focusout.stop="focusout"
    @focusin="onFocusIn"
  />
  <!-- Select from enum values -->
  <x-select
    v-else-if="enumOptions"
    v-model="data"
    :options="enumOptions"
    placeholder="value..."
    :searchable="true"
    :class="{'error-border': error}"
    :read-only="readOnly || schema.readOnly"
    @input="input"
    @focusout.stop="validate"
  />
</template>

<script>
  import primitiveMixin from '../primitive.js'
  import xSelect from '../../../../axons/inputs/Select.vue'
  import xDateEdit from './DateEdit.vue'
  import { validateEmail } from '../../../../../constants/validations'

	export default {
		name: 'XStringEdit',
        components: { xSelect, xDateEdit },
        mixins: [primitiveMixin],
        props: {
		  clearable: {
		    type: Boolean,
            default: true
          }
        },
        data() {
            return {
                data: '',
                valid: true,
                error: ''
            }
        },
        computed: {
            processedData: {
                get() {
                  return this.isUnchangedPassword ? '********' : this.data
                },
                set(new_val) {
                    this.data = new_val
                }
            },
            isEmailValid: function() {
               return (!this.data || validateEmail(this.data)) ? '' : 'error-border';
            },
            isDate() {
		           return (this.schema.format === 'date-time' || this.schema.format === 'date')
            },
            isText() {
                return this.schema.format === 'text'
            },
            isMail() {
               return this.schema.format === 'email'
            },
		        isUnchangedPassword() {
		            return this.inputType === 'password' && this.data && this.data[0] === 'unchanged'
            },
           
            inputType() {
              if (this.schema.format && this.schema.format === 'password') {
                return 'password'
              } else if (this.schema.enum) {
                return ''
              }
              return 'text'
            }
        },
        methods: {
		        formatData() {
              return this.data
            },
            onFocusIn(){
              if(this.isUnchangedPassword){
                this.data = ''
              }
            },
            onValidate (validity) {
                    this.$emit('validate', validity)
            },
            checkData() {
			        return !this.isMail ? true: !this.isEmailValid
		        }
        }
	}
</script>

<style lang="scss">
</style>