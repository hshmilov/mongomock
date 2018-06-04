<template>
    <transition name="modal" @after-enter="$emit('enter')" @after-leave="$emit('leave')">
        <div class="modal-mask" @click.stop="$emit('close')" @keyup.esc="$emit('close')">
            <div class="modal-wrapper">
                <div :class="`modal-container w-${size}`" @click.stop="">
                    <div class="modal-body">
                        <slot name="body" @submit="$emit('confirm')">
                            Are you sure?
                        </slot>
                    </div>
                    <div class="modal-footer">
                        <slot name="footer">
                            <button class="x-btn link" @click="$emit('close')">{{dismissText}}</button>
                            <button class="x-btn" :class="{disabled}" @click="onApprove">{{approveText}}</button>
                        </slot>
                    </div>
                </div>
            </div>
        </div>
    </transition>
</template>

<script>
	export default {
		name: 'modal',
        props: { approveText: { default: 'OK' }, dismissText: { default: 'Cancel' },
            disabled: {default: false}, size: {default: 'xl'} },
        methods: {
			onApprove() {
				if (this.disabled) return
				this.$emit('confirm')
            }
        },
        mounted() {
			if (this.$el.querySelector("input")) {
				this.$el.querySelector("input").focus()
            }
        }
	}
</script>

<style lang="scss">
    .modal-mask {
        position: fixed;
        z-index: 1001;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, .5);
        display: table;
        transition: opacity .3s ease;
        .modal-wrapper {
            display: table-cell;
            vertical-align: middle;
            .modal-container {
                margin: 0 auto;
                padding: 24px;
                background-color: $theme-white;
                border-radius: 2px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, .33);
                transition: all .3s ease;
                .modal-body {
                    padding: 0;
                    margin-bottom: 24px;
                    .form-group:last-of-type {
                        margin-bottom: 0;
                    }
                }
                .modal-footer {
                    border: 0;
                    padding: 0;
                    text-align: right;
                }
            }
        }
    }

    .modal-enter {
        opacity: 0;
    }

    .modal-leave-active {
        opacity: 0;
    }

    .modal-enter .modal-container,
    .modal-leave-active .modal-container {
        transform: scale(1.1);
    }
</style>