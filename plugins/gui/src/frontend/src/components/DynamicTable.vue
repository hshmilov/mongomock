<template>
    <table>
        <thead>
            <tr>
                <th></th>
                <th v-for="field in fields">{{ field.name }}</th>
            </tr>
        </thead>
        <tbody>
            <tr v-for="record in data">
                <td>
                    <checkbox></checkbox>
                </td>
                <td v-for="field in fields">

                </td>
            </tr>
            <tr :colspan="fields.length">
                <td>
                    <a @click="$emit('new')">{{ addNewDataLabel }} </a>
                </td>
            </tr>
        </tbody>
    </table>
</template>

<script>
    import Checkbox from './Checkbox.vue'
    import StatusIcon from './StatusIcon.vue'

	export default {
		name: 'dynamic-table',
        components: { Checkbox, StatusIcon },
        props: ['data', 'fields', 'addNewDataLabel', 'value']
	}
</script>

<style lang="scss">

</style>