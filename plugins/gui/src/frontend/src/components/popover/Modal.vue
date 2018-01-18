<template>
    <transition name="modal">
        <div class="modal-mask" @click.stop="$emit('close')">
            <div class="modal-wrapper">
                <div class="modal-container" @click.stop="$emit('open')">
                    <div class="modal-body">
                        <slot name="body" @submit="$emit('confirm')">
                            Are you sure?
                        </slot>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-inverse" @click="$emit('close')">{{dismissText || 'Cancel'}}</button>
                        <button class="btn" @click="$emit('confirm')">{{approveText || 'OK'}}</button>
                    </div>
                </div>
            </div>
        </div>
    </transition>
</template>

<script>
	export default {
		name: 'modal',
        props: [ 'approveText', 'dismissText'],
        mounted() {
			if (this.$el.querySelector("input")) {
				this.$el.querySelector("input").focus()
            }
        },
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .modal-mask {
        position: fixed;
        z-index: 10001;
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
                width: 600px;
                margin: 0px auto;
                padding: 20px 30px;
                background-color: $background-color-light;
                border-radius: 2px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, .33);
                transition: all .3s ease;
                .modal-body {
                    margin: 20px 0;
                    padding: 0;
                    .form-group:last-of-type {
                        margin-bottom: 0;
                    }
                }
                .modal-footer {
                    border: 0;
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
        -webkit-transform: scale(1.1);
        transform: scale(1.1);
    }
</style>