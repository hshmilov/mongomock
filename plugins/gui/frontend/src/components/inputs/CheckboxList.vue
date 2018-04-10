<template>
    <div class="x-checkbox-list">
        <x-checkbox v-for="item in items" :key="item.name" :value="item.name" :label="item.title"
                    :data="value" @change="$emit('input', $event)" />
    </div>
</template>

<script>
    import xCheckbox from './Checkbox.vue'
	export default {
		name: 'x-checkbox-list',
        components: { xCheckbox },
        props: { items: {required: true}, value: {}}
	}
</script>

<style lang="scss">
    .x-checkbox-list {
        display: flex;
        flex-wrap: wrap;
        margin-top: 16px;
        font-size: 12px;
        color: $theme-black;
        height: 360px;
        overflow: auto;
        align-content: flex-start;
    }
</style>