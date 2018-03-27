<template>
    <div class="section">
        <div class="section-title">
            <i v-if="fontClass" :class="fontClass"></i>
            <svg-icon v-if="iconName" :name="iconName" :original="true" height="20"></svg-icon>
            <div class="title">{{ title }}</div>
        </div>
        <slot></slot>
    </div>
</template>

<script>
	import './icons/action'

	export default {
		name: 'named-section',
        props: ['title', 'fontClass', 'iconName']
	}
</script>

<style lang="scss">

    .section-title {
        padding: 8px 16px;
        .svg-icon {
            overflow: visible;
            .svg-stroke {
                stroke: $color-text-main;
            }
        }
        .title {
            display: inline-block;
        }
    }
</style>