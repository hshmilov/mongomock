<template>
    <div class="x-tooltip" v-show="isActive">
        <div class="content">{{content}}</div>
        <div v-if="dismissible" @click="$emit('input', false)" class="link">GOT IT</div>
    </div>
</template>

<script>
	export default {
		name: 'x-tooltip',
        props: {content: {required: true}, dismissible: {default: false}, value: {}},
        data() {
			return {
				isActive: this.value
            }
        },
        watch: {
			value(newValue) {
                this.isActive = newValue
            }
        }
	}
</script>

<style lang="scss">
    .x-tooltip {
        position: absolute;
        background-color: $theme-white;
        box-shadow: 1px 0 6px 0 rgba(0, 0, 0, 0.2);
        padding: 12px;
        border-radius: 4px;
        right: -4px;
        animation: bounce 1s ease;
        line-height: 24px;
        &:before {
            content: '';
            position: absolute;
            height: 6px;
            width: 6px;
            top: -3px;
            right: 12px;
            box-shadow: 1px 0 6px 0 rgba(0, 0, 0, 0.2);
            transform: rotate(45deg);
            background-color: $theme-white;
        }
        &:after {
            content: '';
            position: absolute;
            height: 8px;
            width: 12px;
            top: 0;
            right: 10px;
            background-color: $theme-white;
        }
        .content {
            width: 200px;
            white-space: pre-wrap;
        }
        .link {
            text-align: right;
        }
    }
</style>