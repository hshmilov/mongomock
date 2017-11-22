<template>
    <div class="status-icon-logo-text">
        <status-icon :value="statusIconValue"></status-icon>
        <img class="logo-container img-lg" :src="`/src/assets/images/logos/${logoValue}.png`" :title="textValue">
        <span class="text-container">{{textValue}}</span>
    </div>
</template>

<script>
    import StatusIcon from './StatusIcon.vue'

	export default {
		name: 'status-icon-logo-text',
        components: { StatusIcon },
        props: ['statusIconValue', 'logoValue', 'textValue']
	}
</script>

<style lang="scss">
    .status-icon-logo-text {
        .status-icon {
            border-radius: 4px;
            line-height: 64px;
            top: 0;
            left: 0;
            position: absolute;
            height: 100%;
        }
        .logo-container {
            margin-left: 24px;
        }
        .text-container {
            margin-left: 12px;
        }
    }
</style>