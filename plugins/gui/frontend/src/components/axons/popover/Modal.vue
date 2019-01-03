<template>
    <transition name="modal" @after-enter="$emit('enter')" @after-leave="$emit('leave')">
        <div class="x-modal">
            <div :class="`modal-container w-${size}`">
                <div class="modal-header" v-if="title">
                    <div class="title">{{ title }}</div>
                    <button class="x-btn link" @click="$emit('close')" v-if="dismissable">x</button>
                </div>
                <div class="modal-body">
                    <slot name="body" @submit="$emit('confirm')">
                        Are you sure?
                    </slot>
                </div>
                <div class="modal-footer">
                    <slot name="footer">
                        <button class="x-btn link" @click="$emit('close')">{{dismissText}}</button>
                        <button class="x-btn" :class="{ disabled }" @click="onApprove" :id="approveId">{{approveText}}</button>
                    </slot>
                </div>
            </div>
            <div class="modal-overlay" @click.stop="$emit('close')" @keyup.esc="$emit('close')"></div>
        </div>
    </transition>
</template>

<script>
    export default {
        name: 'x-modal',
        props: {
            approveText: {default: 'OK'}, approveId: {}, dismissText: {default: 'Cancel'},
            disabled: {default: false}, size: {default: 'xl'}, title: {}, dismissable: {default: false}
        },
        methods: {
            onApprove() {
                if (this.disabled) return
                this.$emit('confirm')
            }
        },
        mounted() {
            if (this.$el.querySelector('input')) {
                this.$el.querySelector('input').focus()
            }
        }
    }
</script>

<style lang="scss">
    .x-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1001;
        display: grid;

        .modal-container {
            margin: auto;
            padding: 24px;
            background-color: $theme-white;
            border-radius: 2px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, .33);
            z-index: 1001;

            .modal-header {
                display: flex;
                border-bottom: 1px solid $grey-2;
                padding: 0 24px 12px;
                margin: 0 -24px 24px -24px;

                .title {
                    flex: 1 0 auto;
                    font-weight: 500;
                    font-size: 16px;
                }
            }

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

        .modal-overlay {
            position: fixed;
            z-index: 1000;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, .5);
            transition: opacity .3s ease;
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