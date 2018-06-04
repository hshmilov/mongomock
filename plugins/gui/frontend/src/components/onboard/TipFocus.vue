<template>
    <div class="x-tip-focus scaling">
        <div class="body">
            <div class="title">{{ title }}</div>
            <div class="content">{{ content }}</div>
            <x-button-dismiss @click.native="$emit('dismiss')"  />
        </div>
    </div>
</template>

<script>
	import xButtonDismiss from './ButtonDismiss.vue'

	export default {
		name: 'x-tip-focus',
        components: { xButtonDismiss },
		props: { title: { required: true }, content: { required: true }, isActive: {} }
	}
</script>

<style lang="scss">
    .x-tip-focus {
        z-index: 500;
        position: absolute;
        width: 50px;
        height: 50px;
        border-radius: 100%;
        border: 60vh solid rgba($theme-orange, 0.96);
        left: -60vh;
        top: -60vh;
        margin-left: 3px;
        margin-top: -5px;
        .body {
            position: absolute;
            top: 8px;
            left: 12vh;
            width: 48vh;
            color: $theme-black;
            .title {
                font-size: 24px;
            }
            .content {
                margin-top: 12px;
                margin-bottom: 24px;
                white-space: pre-wrap;
                font-size: 16px;
            }
            .link {
                color: $theme-black;
                font-size: 16px;
                font-weight: 300;
                &:hover {
                    text-shadow: $text-shadow;
                }
            }
        }
    }
</style>