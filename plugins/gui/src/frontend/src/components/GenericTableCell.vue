<template>
    <td>
        <!--
            Presents given data according to given type in a cell
            Types are: status icon with color, type icon containing icon and text, list of objects or simple text
        -->
        <template v-if="type === 'timestamp'">
            <span>{{ prettyTimestamp(value) }}</span>
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
            <object-list v-if="value && value.length" :type="type" :data="value" :limit="2"></object-list>
        </template>
        <template v-else>
            <span v-bind:class="{wide: wide}" :title="value">{{ value }}</span>
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
        props: ['value', 'type', 'wide'],
        methods: {
            prettyTimestamp(timestamp) {
            	let date = new Date(timestamp)
            	return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
            }
        }
	}
</script>

<style lang="scss">
    .wide {
        height: 3.5em;
        line-height: 1.2em;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }
</style>