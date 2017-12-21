<template>
    <form class="form" @keyup.enter.stop="$emit('submit', model)">
        <div class="row">
            <div v-for="input in schema" class="form-group col-6">
                <label v-if="input.name" class="form-label">{{ input.name }}</label>
                <template v-if="input.control === 'select'">
                    <select class="form-control" v-model="model[input.path]" @input="$emit('input', model)">
                        <option v-for="option in input.options">{{ option.text }}</option>
                    </select>
                </template>
                <template v-else-if="input.control === 'multiple-select'">
                    <multiple-select :title="`Select ${input.name}:`" :items="input.options" :type="input.type"
                                     v-model="model[input.path]" @input="$emit('input', model)">
                    </multiple-select>
                </template>
                <template v-else-if="input.control === 'bool'">
                    <checkbox v-model="model[input.path]" @change="$emit('input', model)"></checkbox>
                </template>
                <template v-else>
                    <input class="form-control" :type="input.control" :placeholder="input.placeholder"
                           v-model="model[input.path]" @input="convertValue(input.path, input.control)">
                </template>
            </div>
            <div v-if="submitLabel" class="form-group col-1">
                <a class="btn" @click="$emit('submit', model)">{{ submitLabel }}</a>
            </div>
        </div>
    </form>
</template>

<script>
    import MultipleSelect from './MultipleSelect.vue'
    import Checkbox from './Checkbox.vue'

    export default {
        name: 'generic-form',
        components: { MultipleSelect, Checkbox },
        props: [ 'schema', 'submitLabel', 'value' ],
        computed: {
            pathByName() {
                return this.schema.reduce(function(map, input) {
                    map[input.name] = input.path
                    return map
                }, {})
            }
        },
        data() {
			return {
				model: {...this.value}
			}
		},
        watch: {
        	value: function(newValue) {
        		this.model = { ...newValue }
            }
        },
        methods: {
        	convertValue(path, type) {
        		if (type === "number") {
        			if (!this.model[path]) {
						this.model[path] = undefined
                    } else {
						this.model[path] = parseInt(this.model[path])
					}
                }
				this.$emit('input', this.model)
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .form {
        .form-group {
            &.col-3, &.col-1 {
                margin-bottom: 0;
            }
            &.col-1 {
                position: relative;
                .btn {
                    overflow: visible;
                    position: absolute;
                    bottom: 12px;
                }
            }
            .image-list {
                line-height: 30px;
            }
        }
        .form-control {
            height: 30px;
            &:focus {
                border-color: $color-theme-light;
            }
        }
        .form-label {
            font-size: 14px;
            &.form-view {
                margin-bottom: .5rem;
                display: block;
                &:hover {
                    color: $color-theme-light;
                }
            }
        }
        &.row {
            margin: 12px -12px;
        }
    }

</style>