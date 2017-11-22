<template>
    <span class="status-icon">
        <i v-if="value === 'error'" class="icon-exclamation-triangle error-fill"></i>
        <i v-else-if="value === 'warning'" class="icon-exclamation-triangle warning-fill"></i>
        <i v-else-if="value === 'success'" class="icon-check success-fill"></i>
    </span>
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
        color: $color-light;
        i {
            padding: 4px;
            border-radius: 4px;
        }
    }
</style>