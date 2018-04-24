<template>
    <form class="form" @keyup.enter.stop="$emit('submit', model)">
        <div v-bind:class="{'row': !vertical}">
            <div v-for="input in schema" v-bind:class="{ 'col-6': !vertical, 'row': vertical }">
                <div class="form-group">
                    <label v-if="input.name" class="form-label">{{ input.name }}</label>
                    <template v-if="input.control === 'select'">
                        <select class="form-control" v-model="model[input.path]"
                                @input="convertValue(input.path, input.control)" :ref="'fields'">
                            <option v-for="option in input.options">{{ option.text }}</option>
                        </select>
                    </template>
                    <template v-else-if="input.control === 'bool'">
                        <checkbox v-model="model[input.path]" @change="convertValue(input.path, input.control)"></checkbox>
                    </template>
                    <template v-else-if="input.control === 'array'">
                        <input type="file" @change="uploadFile" :name="input.path">
                    </template>
                    <template v-else>
                        <input class="form-control" :type="input.control" :placeholder="input.placeholder"
                               v-model="model[input.path]" @input="convertValue(input.path, input.control)" :ref="'fields'">
                    </template>
                </div>
            </div>
            <div v-bind:class="{ 'col-6': !vertical, 'row': vertical }">
                <div v-if="submitLabel" class="form-group btn-group" v-bind:class="{ 'col-1': condensed }">
                    <a class="btn" @click="$emit('submit', model)">{{ submitLabel }}</a>
                </div>
            </div>
        </div>
    </form>
</template>

<script>
    import Checkbox from './Checkbox.vue'

    export default {
        name: 'generic-form',
        components: { Checkbox },
        props: [ 'schema', 'submitLabel', 'condensed', 'value', 'vertical' ],
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
        	uploadFile(uploadEvent) {
				const files = uploadEvent.target.files || e.dataTransfer.files
				if (!files.length) return

                const name = uploadEvent.target.name
				let reader = new FileReader()
                const vm = this
				reader.onload = (loadEvent) => {
					vm.model[name] = Array.prototype.slice.call(new Uint8Array(loadEvent.target.result))
					this.$emit('input', this.model)
				}
				reader.readAsArrayBuffer(files[0])
            },
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
        },
        mounted() {
        	if (this.$refs.fields) {
				this.$refs.fields[0].focus()
			}
        }
    }
</script>

<style lang="scss">

    .form {
        .row > .form-group {
            width: 100%;
            margin-left: -10px;
            margin-right: -10px;
            .btn {
                margin: auto;
            }
        }
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