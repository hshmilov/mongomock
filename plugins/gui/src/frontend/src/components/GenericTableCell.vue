<template>
    <td>
        <!--
            Presents given data according to given type in a cell
            Types are: status icon with color, type icon containing icon and text, list of objects or simple text
        -->
        <template v-if="type === 'timestamp'">
            <span>{{ parseDate(value)}} {{parseTime(value) }}</span>
        </template>
        <template v-else-if="type === 'status'">
            <status-icon :value="value"></status-icon>
        </template>
        <template v-else-if="type === 'status-icon-logo-text'">
            <status-icon-logo-text :textValue="value.text"
                                   :logoValue="value.logo"
                                   :statusIconValue="value.status"></status-icon-logo-text>
        </template>
        <template v-else-if="type === 'type'">
            <type-icon :value="value"></type-icon>
        </template>
        <template v-else-if="type && type.indexOf('list') > -1">
            <object-list v-if="value && value.length" :type="type" :data="value" :limit="3"></object-list>
        </template>
        <template v-else>
            <span>{{ value }}</span>
        </template>
    </td>
</template>

<script>
	import ObjectList from './ObjectList.vue'
	import StatusIcon from './StatusIcon.vue'
    import StatusIconLogoText from './StatusIconLogoText.vue'
	import TypeIcon from './TypeIcon.vue'

	export default {
		name: 'generic-table-cell',
        components: {ObjectList, StatusIcon, StatusIconLogoText, TypeIcon},
        props: ['value', 'type'],
        methods: {
			pad2(number) {
				/*
				    Add leading zero for 1 digit numbers - to keep a constant format of date and time
				 */
				if ((number + '').length >= 2) { return number }
				return `0${number}`
			},
			parseDate(timestamp) {
				/*
                    Convert given timestamp to a date by the format dd/mm/yyyy
				 */
				let d = new Date(timestamp)
				return [this.pad2(d.getDate()), this.pad2(d.getMonth()+1), this.pad2(d.getFullYear())].join('/')
			},
			parseTime(timestamp) {
				/*
				    Convert given timestamp to a time by the format hh:mm
				 */
				let d = new Date(timestamp)
				return [this.pad2(d.getHours()), this.pad2(d.getMinutes())].join(':')
			},
        }
	}
</script>

<style lang="scss">

</style>