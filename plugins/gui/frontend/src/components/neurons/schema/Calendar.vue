<template>
    <div class="x-calendar">
        <div class="calendar-details" v-if="details">
            <img :src="require(`Logos/adapters/${details.image}.png`)" height="48"/>
            <div v-for="field in details.fields">{{ field }}</div>
        </div>
        <div class="calendar-view">
            <x-button link @click="decCurrentWeek">&lt;</x-button>
            <div v-for="day in currentWeekDays" class="day">
                <div class="day-title">
                    <div>{{day.name}}</div>
                    <div>{{day.date.toDate().toLocaleDateString()}}</div>
                </div>
                <component v-if="day.instance_details" :is="details.program_type" :data="day" class="day-body"/>
            </div>
            <x-button link @click="incCurrentWeek">&gt;</x-button>
        </div>
    </div>
</template>

<script>
    import dose from '../../networks/health/PrescriptionDose.vue'
    import bolus from '../../networks/health/PrescriptionBolus.vue'
    import moment from 'moment'
    import xButton from '../../axons/inputs/Button.vue'

    export default {
        name: 'x-calendar',
        components: {dose, bolus, xButton},
        props: {data: {required: true}, schema: {}},
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
                        return {date: day, name: day.format('ddd')}
                    }
                    // Found data matching current date, proceed to next one and return the current
                    dataIndex++
                    return {...this.currentWeekData[dataIndex - 1], date: day, name: day.format('ddd')}
                })
            }
        },
        data() {
            return {
                currentWeek: moment().isoWeek(),
                currentYear: moment().year()
            }
        },
        methods: {
            incCurrentWeek() {
                let nextWeek = this.currentDate.clone().add(1, 'weeks')
                this.currentWeek = nextWeek.isoWeek()
                this.currentYear = nextWeek.year()
            },
            decCurrentWeek() {
                let prevWeek = this.currentDate.clone().subtract(1, 'weeks')
                this.currentWeek = prevWeek.isoWeek()
                this.currentYear = prevWeek.year()
            }
        },
        created() {
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
    .x-calendar {
        display: flex;
        flex-direction: row;
        height: 100%;

        .calendar-details {
            margin-left: 24px;
            margin-top: 84px;
            width: 200px;
            font-weight: 500;
            font-size: 16px;

            .x-schema-custom {
                display: block;
            }
        }

        .calendar-view {
            flex: auto 1 0;
            height: 100%;
            width: calc(100% - 200px);
            display: grid;
            grid-template-columns: 1fr repeat(7, 4fr) 1fr;

            .x-button.link {
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
                }

                &:nth-child(2) .day-body {
                    border-left: 2px solid $grey-2;
                }
            }
        }
    }
</style>