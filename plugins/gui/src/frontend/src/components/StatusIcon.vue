<template>
    <div :class="`status-icon ${value}-fill`">
        <i v-if="value === 'error'" class="icon-exclamation-triangle"></i>
        <i v-else-if="value === 'warning'" class="icon-exclamation-triangle"></i>
        <i v-else-if="value === 'info'" class="icon-info"></i>
        <i v-else-if="value === 'success'" class="icon-check-alt"></i>
    </div>
</template>

<script>
	export default {
		name: 'status-icon',
        props: ['value']
	}
</script>

<style lang="scss">
    @import '../scss/config';

    .status-icon {
        display: inline-block;
        color: $color-light;
        border-radius: 4px;
        background-color: $background-color-disabled;
        i {
            padding: 5px;
            vertical-align: middle;
        }
    }
</style>