<template>
    <form class="form" @keyup.enter.stop="$emit('submit', model)">
        <div class="row">
            <div v-for="input in schema" class="form-group col-3">
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
                <template v-else-if="input.control === 'checkbox'">
                    <checkbox :label="input.name" v-model="model[input.path]"></checkbox>
                </template>
                <template v-else>
                    <input class="form-control" :type="input.control" :placeholder="input.placeholder"
                           v-model="model[input.path]" @input="$emit('input', model)">
                </template>
            </div>
            <div class="form-group col-1">
                <a v-if="submitLabel" class="btn" @click="$emit('submit', model)">{{ submitLabel }}</a>
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
                    bottom: 0;
                }
            }
            .image-list {
                line-height: 30px;
            }
        }
        .form-control {
            height: 30px;
            &:focus {
                border-color: $color-theme;
            }
        }
        .form-label {
            font-size: 14px;
            &.form-view {
                margin-bottom: .5rem;
                display: block;
                &:hover {
                    color: $color-theme;
                }
            }
        }
        &.row {
            margin: 12px -12px;
        }
    }
    .form-material {
        .form-group {
            overflow: hidden;
            .form-control {
                background-color: rgba(0, 0, 0, 0);
                background-position: center bottom, center calc(100% - 1px);
                background-repeat: no-repeat;
                background-size: 0 2px, 100% 1px;
                padding: 0;
                transition: background 0s ease-out 0s;
                height: 30px;
            }
            &.col, &.col-1 {
                margin-bottom: 0;
            }
            &.col-1 {
                text-align: center;
                vertical-align: middle;
                line-height: 50px;
                overflow: visible;
            }
        }
        &.row {
            margin: 20px -15px;
        }

        .form-control,
        .form-control.focus,
        .form-control:focus {
            background-image: linear-gradient($color-theme, $color-theme), linear-gradient($border-color, $border-color);
            border: 0 none;
            border-radius: 0;
            box-shadow: none;
            float: none;
        }

        .form-control.focus,
        .form-control:focus {
            background-size: 100% 2px, 100% 1px;
            outline: 0 none;
            transition-duration: 0.3s;
        }
    }

</style>