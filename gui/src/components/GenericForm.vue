<template>
    <form class="form" v-bind:class="{ 'row': horizontal }" @keyup.enter.stop="submitHandler">
        <template v-if="advancedView === undefined || !advancedView">
            <div v-for="input in schema" class="form-group" v-bind:class="{ 'col': horizontal }">
                <label v-if="input.name" class="form-label">{{ input.name }}</label>
                <template v-if="input.type === 'select'">
                    <select class="form-control" size v-model="values[input.path]">
                        <option v-for="option in input.options">{{ option.text }}</option>
                    </select>
                </template>
                <template v-else-if="input.type === 'multiple-select'">
                    <multiple-select :title="`Select ${input.name}:`" :items="input.options"
                                     v-model="values[input.path]"></multiple-select>
                </template>
                <template v-else-if="input.type === 'checkbox'">
                    <checkbox :label="input.name" v-model="values[input.path]"></checkbox>
                </template>
                <template v-else>
                    <input class="form-control" :type="input.type"
                           v-model="values[input.path]" :placeholder="input.placeholder">
                </template>
            </div>
        </template>
        <template v-else>
            <div class="form-group" v-bind:class="{ 'col': horizontal }">
                <label class="form-label">Search:</label>
                <input class="form-control" type="text" v-model="advancedQuery" @change="parseAdvancedQuery">
            </div>
        </template>
        <div class="form-group" v-bind:class="{ 'col-1': horizontal }">
            <a class="form-label form-view" @click="advancedView = false" v-if="advancedView">Basic</a>
            <a class="form-label form-view" @click="advancedView = true" v-else>Advanced</a>
            <a v-if="submitHandler !== undefined" class="btn btn-info"
               v-on:click="submitHandler">{{ submitLabel || 'Send' }}</a>
        </div>
    </form>
</template>

<script>
    import MultipleSelect from './MultipleSelect.vue'
    import Checkbox from './Checkbox.vue'

    export default {
        name: 'generic-form',
        components: { MultipleSelect, Checkbox },
        props: [ 'schema', 'values', 'submitHandler', 'submitLabel', 'horizontal' ],
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
                advancedView: false,
                advancedQuery: ''
            }
        },
        watch: {
            advancedView(newAdvancedView) {
                if (!newAdvancedView) { return }
                this.advancedQuery = this.buildAdvancedQuery()
            }
        },
        methods: {
            buildAdvancedQuery() {
                let advancedQueryParts = []
                let values = this.values
                this.schema.forEach(function(input) {
                    if (values[input.path] === undefined || !values[input.path]) { return }
                    if ((input.type === 'text') || (input.type === 'select')) {
                        advancedQueryParts.push(`${input.name}=${values[input.path]}`)
                    } else if (input.type === 'multiple-select') {
                        advancedQueryParts.push(`${input.name} in (${values[input.path]})`)
                    }
                })
                return advancedQueryParts.join(' AND ')
            },
            parseAdvancedQuery() {
                let _this = this
                let advancedQueryParts = this.advancedQuery.split(' AND ')
                advancedQueryParts.forEach(function(part) {
                    let match = part.match(/(.*)(=| in )(.*)/);
                    if (match !== undefined && match.length > 3) {
                    	if (_this.pathByName[match[1]] !== undefined) {
                            _this.values[_this.pathByName[match[1]]] = match[3]
                        } else {
							_this.values[match[1]] = match[3]
                        }
                    }
                })
            }
        }
    }
</script>

<style lang="scss">
    @import '../assets/scss/config';

    .form {
        .form-group {
            &.col, &.col-1 {
                margin-bottom: 0;
            }
            &.col-1 {
                text-align: left;
                overflow: visible;
                .btn.btn-info {
                    vertical-align: bottom;
                    color: $color-light;
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
        .btn.btn-info {
            cursor: pointer;
            padding: 4px 12px;
            background: $color-theme;
            border: 1px solid $color-theme;
            -webkit-box-shadow: 0 2px 2px 0 rgba($color-theme, 0.14), 0 3px 1px -2px rgba($color-theme, 0.2), 0 1px 5px 0 rgba(66, 165, 245, 0.12);
            box-shadow: 0 2px 2px 0 rgba($color-theme, 0.14), 0 3px 1px -2px rgba($color-theme, 0.2), 0 1px 5px 0 rgba($color-theme, 0.12);
            -webkit-transition: 0.2s ease-in;
            -o-transition: 0.2s ease-in;
            transition: 0.2s ease-in;
            &:hover {
                -webkit-box-shadow: 0 14px 26px -12px rgba($color-theme, 0.42), 0 4px 23px 0 rgba(0, 0, 0, 0.12), 0 8px 10px -5px rgba($color-theme, 0.2);
                box-shadow: 0 14px 26px -12px rgba($color-theme, 0.42), 0 4px 23px 0 rgba(0, 0, 0, 0.12), 0 8px 10px -5px rgba($color-theme, 0.2);
            }
        }
        &.row {
            margin: 12px -15px;
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