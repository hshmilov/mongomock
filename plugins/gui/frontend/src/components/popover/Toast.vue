<template>
    <div class="x-toast" :style="{ left }">
        <div class="content">{{ message }}</div>
        <div class="actions">
            <slot />
        </div>
    </div>
</template>

<script>
	export default {
		name: 'x-toast',
        props: { message: { required: true }, timed: { default: true } },
        data() {
			return {
				left: ''
            }
        },
        watch: {
			message() {
				this.left = ''
            }
        },
        methods: {
			getLeftPos() {
				return `calc(50vw - ${this.$el.offsetWidth / 2}px)`
            }
        },
        mounted() {
			if (this.timed) {
			    setTimeout(() => this.$emit('done'), 4000)
            }
            this.left = this.getLeftPos()
        },
        updated() {
			if (!this.left) {
                this.left = this.getLeftPos()
            }
        }
	}
</script>

<style lang="scss">
    .x-toast {
        position: fixed;
        z-index: 500;
        top: 24px;
        padding: 0 12px;
        background: $theme-black;
        color: $theme-white;
        border-radius: 4px;
        box-shadow: 0 1px 1px rgba(0, 0, 0, .2);
        height: 32px;
        display: flex;
        justify-content: space-between;
        animation: bounce 1s ease;
        .content {
            line-height: 32px;
        }
        .actions {
            color: $theme-orange;
        }
    }
</style>