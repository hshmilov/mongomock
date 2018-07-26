<template>
    <div class="x-prescription-dose">
        <div class="dose-list">
            <div v-for="dose, index in data.instance_details" class="dose-item">
                <div v-if="index" class="dose-link"></div>
                <div @click="selectData(index)" class="dose-container" :class="{selected: selectedData === index}">
                    <div>
                        <x-dose :percentage="dose.percentage_of_volume_infused * 100"
                                :placeholder="dose.instance_state === 'Upcoming'" />
                        <x-cross v-if="dose.instance_state === 'Missed'" />
                        <div v-if="dose.instance_state === 'Missing Record'" class="unknown">?</div>
                    </div>
                    <div class="dose-summary" v-if="dose.instance_state === 'Taken'">
                        <div>{{dose.vi}} {{dose.vi_units}}</div>
                        <div class="dose-time">{{formatShortTime(dose.start_ts)}} - {{formatShortTime(dose.end_ts)}}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="dose-details">
            <x-array-view v-if="selectedData !== null" class="growing-y"
                          :value="data.instance_details[selectedData]" :schema="detailsSchema" />
        </div>
    </div>
</template>

<script>
	import xDose from '../../patterns/Dose.vue'
    import xCross from '../../patterns/Cross.vue'
	import xArrayView from '../../controls/array/ArrayView.vue'

	export default {
		name: 'prescription-dose',
        components: { xDose, xCross, xArrayView },
        props: { data: { required: true }},
        computed: {
            detailsSchema() {
                return {
                    type: 'array', items: [
                        { type: 'string', title: 'Dose Number', name: 'dose_number' },
                        { type: 'string', title: 'Dose State', name: 'instance_state' },
                        { type: 'number', title: 'Percentage Infused', name: 'percentage_of_volume_infused', format: 'percentage' }
                    ]
                }
            },
            currentDate() {
            	return this.data.date.toDate().toLocaleDateString()
            }
        },
        data() {
			return {
				selectedData: null
            }
        },
        watch: {
			currentDate() {
				this.selectedData = null
            }
        },
        methods: {
			selectData(dataItem, day) {
				this.selectedData = null
				setTimeout(() => this.selectedData = dataItem, 100)
			},
			formatShortTime(timestamp) {
				let date = new Date(timestamp)
				return `${this.padZero(date.getHours())}:${this.padZero(date.getSeconds())}`
			},
			padZero(number) {
				return ("0" + number).slice(-2)
			}
        }
	}
</script>

<style lang="scss">
    .x-prescription-dose {
        display: flex;
        flex-direction: column;
        .dose-list {
            flex: 1 0 auto;
            .dose-item {
                margin: -12px;
                padding: 12px;
                &:nth-child(odd) {
                    background-color: rgba($grey-1, 0.6);
                }
                .dose-link {
                    height: 24px;
                    width: 2px;
                    background-color: $theme-blue;
                    margin-left: 14px;
                    margin-top: -12px;
                }
                .dose-container {
                    cursor: pointer;
                    border-radius: 4px;
                    opacity: 0.6;
                    height: 48px;
                    position: relative;
                    display: flex;
                    flex-direction: row;
                    &:hover, &.selected {
                        opacity: 1;
                    }
                    .cross {
                        position: absolute;
                        top: 10px;
                        left: 6px;
                    }
                    .unknown {
                        font-size: 24px;
                        position: absolute;
                        top: 0px;
                        left: 6px;
                    }
                    .dose-summary {
                        flex: 1 0 auto;
                        margin-left: 8px;
                        .dose-time {
                            font-size: 12px;
                        }
                    }
                }
            }
        }
        .dose-details {
            padding-top: 12px;
            border-top: 1px solid $theme-orange;
            overflow: hidden;
            height: 200px;
            .x-array-view {
                overflow: auto;
                height: 100%;
                font-size: 12px;
            }
        }
    }
</style>