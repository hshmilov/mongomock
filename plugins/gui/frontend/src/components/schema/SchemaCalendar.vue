<template>
    <div class="x-schema-calendar">
        <div class="calendar-details">
            <img :src="`/src/assets/images/logos/${details.image}.png`" height="48" />
            <div>{{ details.name }}</div>
            <div>{{ details.volume }}</div>
            <div>{{ details.type }}</div>
        </div>
        <div class="calendar-view">
            <div @click="decCurrentWeek" class="x-btn link">&lt;</div>
            <div v-for="day in currentWeekDays" class="day">
                <div class="day-title">
                    <div>{{day.name}}</div>
                    <div>{{day.date.toDate().toLocaleDateString()}}</div>
                </div>
                <div class="day-body">
                    <div class="day-list">
                        <div v-for="dose, index in day.instance_details" class="day-slot">
                            <div v-if="index" class="slot-link"></div>
                            <div @click="selectData(index, day.name)" class="slot-dose" :class="{
                                    selected: selectedDataByDay[day.name] === index
                                 }">
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
                    <div class="day-details">
                        <x-array-view v-if="selectedDataByDay[day.name] !== null" class="growing-y"
                                      :value="day.instance_details[selectedDataByDay[day.name]]" :schema="detailsSchema" />
                    </div>
                </div>
            </div>
            <div @click="incCurrentWeek" class="x-btn link">&gt;</div>
        </div>
    </div>
</template>

<script>
    import xCross from '../patterns/Cross.vue'
    import xArrayView from '../controls/array/ArrayView.vue'
    import xDose from '../patterns/Dose.vue'
    import moment from 'moment'

	export default {
		name: 'x-schema-calendar',
        components: { xCross, xArrayView, xDose },
        props: { data: { required: true }, schema: { } },
        computed: {
			calendar() {
				if (!this.data) return {}
				return this.data.calendar
            },
            details() {
				if (!this.data) return {}
				return this.data.prescription_program
            },
			dataWeeks() {
				return Object.keys(this.calendar)
            },
            currentDays() {
            	/* List of dates to present, according to currently selected week */
                let days = []
                for (let i = 0; i < 7; i++) {
            		// Create each consecutive date, in the range of 7 days
                    days.push(this.currentWeekStart.clone().add(i, 'days'))
                }
                return days
            },
            currentDate() {
            	/* Create date object from current year and week */
            	return moment().year(this.currentYear).isoWeek(this.currentWeek)
            },
            currentWeekStart() {
				/* Find the date of the Monday, for the given week of given year */
				return this.currentDate.clone().startOf('isoWeek')
            },
            currentWeekData() {
				return this.calendar[`${this.currentYear}_${this.currentWeek}`]
            },
            currentWeekDays() {
				let dataIndex = 0
                return this.currentDays.map(day => {
                	/* Check for data of this day or just return the day, if none found */
                	if (!this.currentWeekData || dataIndex === this.currentWeekData.length
                        || !moment(this.currentWeekData[dataIndex].date).isSame(day, 'day')) {
                		// No data received for this day so return the date only
                        return { date: day, name: day.format('ddd') }
                    }
                    // Found data matching current date, proceed to next one and return the current
                    dataIndex++
                    return { ...this.currentWeekData[dataIndex - 1], date: day, name: day.format('ddd') }
                })
            },
            detailsSchema() {
				return {
					type: 'array', items: [
                        { type: 'string', title: 'Dose Number', name: 'dose_number' },
                        { type: 'string', title: 'Dose State', name: 'instance_state' },
                        { type: 'number', title: 'Percentage Infused', name: 'percentage_of_volume_infused', format: 'percentage' }
                    ]
                }
            }
        },
        data() {
			return {
				currentWeek: moment().isoWeek(),
                currentYear: moment().year(),
                selectedDataByDay: {}
            }
        },
        methods: {
            incCurrentWeek() {
                let nextWeek = this.currentDate.clone().add(1, 'weeks')
                this.currentWeek = nextWeek.isoWeek()
                this.currentYear = nextWeek.year()
				this.initSelectedDataByDay()
            },
            decCurrentWeek() {
				let prevWeek = this.currentDate.clone().subtract(1, 'weeks')
				this.currentWeek = prevWeek.isoWeek()
				this.currentYear = prevWeek.year()
                this.initSelectedDataByDay()
            },
            selectData(dataItem, day) {
            	this.selectedDataByDay[day] = null
                setTimeout(() => this.selectedDataByDay[day] = dataItem, 100)

            },
            initSelectedDataByDay() {
            	this.selectedDataByDay = {
					'Mon': null, 'Tue': null, 'Wed': null, 'Thu': null, 'Fri': null, 'Sat': null, 'Sun': null
				}
            },
            formatShortTime(timestamp) {
            	let date = new Date(timestamp)
                return `${this.padZero(date.getHours())}:${this.padZero(date.getSeconds())}`
            },
            padZero(number) {
            	return ("0" + number).slice(-2)
            }
        },
        created() {
			this.initSelectedDataByDay()
			if (this.currentWeekData) return

			let minDateDiff = Infinity
            // Find week in data closest to current
            this.dataWeeks.forEach(week => {
				let weekParts = week.split('_').map(part => parseInt(part))
				let currentDateDiff = this.currentDate.diff(moment().year(weekParts[0]).isoWeek(weekParts[1]))
                if (currentDateDiff < minDateDiff) {
					// Current diff is smaller so current date is closer than previous
            		minDateDiff = currentDateDiff
					this.currentYear = weekParts[0]
					this.currentWeek = weekParts[1]
                }
            })
        }
	}
</script>

<style lang="scss">
    .x-schema-calendar {
        display: flex;
        flex-direction: row;
        height: 100%;
        .calendar-details {
            margin-right: 24px;
            .custom-data {
                display: block;
            }
        }
        .calendar-view {
            flex: auto 1 0;
            height: 100%;
            display: grid;
            grid-template-columns: 1fr repeat(7, 4fr) 1fr;
            .x-btn.link {
                padding: 0 8px;
                font-size: 24px;
            }
            .day {
                display: flex;
                flex-direction: column;
                .day-title {
                    font-weight: 400;
                    color: $grey-4;
                    text-align: center;
                    border-bottom: 2px dotted $grey-2;
                }
                .day-body {
                    border-right: 2px solid $grey-2;
                    flex: 1 0 auto;
                    padding: 12px;
                    display: flex;
                    flex-direction: column;
                    .day-list {
                        flex: 1 0 auto;
                        .day-slot {
                            margin: -12px;
                            padding: 12px;
                            &:nth-child(odd) {
                                background-color: rgba($grey-1, 0.6);
                            }
                            .slot-link {
                                height: 24px;
                                width: 2px;
                                background-color: $theme-blue;
                                margin-left: 14px;
                                margin-top: -12px;
                            }
                            .slot-dose {
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
                    .day-details {
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
                &:nth-child(2) .day-body {
                    border-left: 2px solid $grey-2;
                }
            }
        }
    }
</style>