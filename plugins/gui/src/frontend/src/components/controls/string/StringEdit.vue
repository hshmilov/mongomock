<template>
    <input v-if="inputType" :id="schema.name" :type="inputType" v-model="data" :class="{'invalid': !valid}"
           @focusout.stop="handleData"/>
    <div v-else-if="schema.format === 'date-time'">
        <!-- Date Picker -->
        <x-date-edit v-model="data" @input="handleData"></x-date-edit>
    </div>
    <div v-else-if="schema.enum">
        <!-- Select from enum values -->
        <select :class="{'invalid': !valid}" placeholder="Select value...">
            <option v-for="item in schema.enum">{{item}}</option>
        </select>
    </div>
</template>

<script>
	import PrimitiveMixin from '../primitive.js'
    import xDateEdit from './DateEdit.vue'

	export default {
		name: 'x-string-edit',
        mixins: [PrimitiveMixin],
        components: { xDateEdit },
        computed: {
            inputType() {
				if (this.schema.format && this.schema.format === 'password') {
					return 'password'
                } else if ((this.schema.format && this.schema.format === 'date-time') || this.schema.enum) {
					return ''
                }
                return 'text'
            }
        }
	}
</script>

<style lang="scss">
    @import '../../../scss/config';

    .cov-vue-date {
        width: 100%;
        position: relative;
        .datepicker-overlay {
            position: relative !important;
            overflow: visible !important;
            .cov-date-body {
                position: absolute;
                -webkit-transform: none;
                -moz-transform: none;
                -ms-transform: none;
                -o-transform: none;
                transform: none;
                top: 0;
                left: 0;
                .cov-date-monthly, .cov-date-box, .button-box {
                    font-family: Poppins, sans-serif;
                    .hour-box, .min-box {
                        .hour-item, .min-item {
                            font-size: 20px !important;
                            &.active {
                                background-color: $color-theme-light;
                            }
                        }
                    }
                }
                .cov-date-monthly {
                    height: 40px;
                    padding: 4px;
                    .cov-date-caption {
                        padding: 0 !important;
                        height: 40px;
                        direction: rtl;
                        width: 80%;
                        br { display: none; }
                    }
                    .cov-date-previous, .cov-date-next {
                        height: 40px;
                        width: 10% !important;
                        &::before, &::after {
                            width: 10px;
                        }
                        &::after {
                            margin-top: 0;
                        }
                    }
                }
                .cov-date-box {
                    height: 200px;
                    .cov-picker-box {
                        padding: 0;
                        height: 200px;
                        overflow: hidden;
                        .week {
                            background-color: $color-theme-dark !important;
                            ul li {
                                color: $color-theme-light !important;
                                font-weight: 200 !important;
                            }
                        }
                        .day.checked {
                            background-color: $color-theme-light !important;
                        }
                    }
                }
            }
        }
    }
</style>