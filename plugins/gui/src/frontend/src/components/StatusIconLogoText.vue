<template>
    <div class="status-icon-logo-text">
        <status-icon v-if="statusIconValue" :value="statusIconValue"></status-icon>
        <img class="logo-container img-lg" v-bind:class="{'ml-4': statusIconValue}"
             :src="`/src/assets/images/logos/${logoValue}.png`" :title="textValue">
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
            top: 0;
            left: 0;
            position: absolute;
            width: 24px;
            height: 100%;
            i {
                position: absolute;
                top: 40%;
                left: 0;
            }
        }
        .text-container {
            margin-left: 12px;
        }
    }
</style>