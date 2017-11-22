<template>
    <td>
        <template v-if="type === 'timestamp'">
            <span>{{ parseDate(value)}} {{parseTime(value) }}</span>
        </template>
        <template v-else-if="type === 'status'">
            <status-icon :value="value"></status-icon>
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
	import TypeIcon from './TypeIcon.vue'

	export default {
		name: 'generic-table-cell',
        components: {ObjectList, StatusIcon, TypeIcon},
        props: ['value', 'type'],
        methods: {
			pad2(number) {
				if ((number + '').length === 2) { return number }
				return `0${number}`
			},
			parseDate(timestamp) {
				let d = new Date(timestamp)
				return `${this.pad2(d.getDate())}/${this.pad2(d.getMonth()+1)}/${this.pad2(d.getFullYear())}`
			},
			parseTime(timestamp) {
				let d = new Date(timestamp)
				return `${this.pad2(d.getHours())}:${this.pad2(d.getMinutes())}`
			},
        }
	}
</script>

<style lang="scss">

</style>