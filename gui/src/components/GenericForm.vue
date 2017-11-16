<template>
    <form class="form" v-bind:class="{ 'row': horizontal }" @keyup.enter.stop="submitHandler(queryValues)">
        <template v-if="advancedView === undefined || !advancedView">
            <div v-for="input in schema" class="form-group" v-bind:class="{ 'col': horizontal }">
                <label v-if="input.name" class="form-label">{{ input.name }}</label>
                <template v-if="input.type === 'select'">
                    <select class="form-control" size v-model="queryValues[input.path]">
                        <option v-for="option in input.options">{{ option.text }}</option>
                    </select>
                </template>
                <template v-else-if="input.type === 'multiple-select'">
                    <multiple-select :title="`Select ${input.name}:`" :items="input.options"
                                     v-model="queryValues[input.path]"></multiple-select>
                </template>
                <template v-else-if="input.type === 'checkbox'">
                    <checkbox :label="input.name" v-model="queryValues[input.path]"></checkbox>
                </template>
                <template v-else>
                    <input class="form-control" :type="input.type"
                           v-model="queryValues[input.path]" :placeholder="input.placeholder">
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
            <a v-if="values !== undefined" class="btn btn-confirm"
               v-on:click="submitHandler(queryValues)">{{ submitLabel || 'Send' }}</a>
        </div>
    </form>
</template>

<script>
    import MultipleSelect from './MultipleSelect.vue'
    import Checkbox from './Checkbox.vue'

    export default {
        name: 'generic-form',
        components: { MultipleSelect, Checkbox },
        props: [ 'schema', 'submitLabel', 'horizontal', 'values', 'submitHandler' ],
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
                advancedQuery: '',
                queryValues: { ...this.values }
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
                this.schema.forEach((input) => {
                    if (this.queryValues[input.path] === undefined || !this.queryValues[input.path]) { return }
                    if ((input.type === 'text') || (input.type === 'select')) {
                        advancedQueryParts.push(`${input.name}=${this.queryValues[input.path]}`)
                    } else if (input.type === 'multiple-select') {
                        advancedQueryParts.push(`${input.name} in (${this.queryValues[input.path]})`)
                    }
                })
                return advancedQueryParts.join(' AND ')
            },
            parseAdvancedQuery() {
                let advancedQueryParts = this.advancedQuery.split(' AND ')
                advancedQueryParts.forEach((part) => {
                    let match = part.match(/(.*)(=| in )(.*)/)
                    if (match !== undefined && match.length > 3) {
                    	if (this.pathByName[match[1]] !== undefined) {
                            this.queryValues[_this.pathByName[match[1]]] = match[3]
                        } else {
							this.queryValues[match[1]] = match[3]
                        }
                    }
                })
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .form {
        .form-group {
            &.col, &.col-1 {
                margin-bottom: 0;
            }
            &.col-1 {
                text-align: left;
                overflow: visible;
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