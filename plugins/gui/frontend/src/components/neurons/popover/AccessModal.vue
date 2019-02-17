<template>
    <x-modal v-if="value" @close="dismissAccessMessage">
        <div slot="body">You do not have permission to access the {{ value }} screen</div>
        <div slot="footer">
            <x-button @click="dismissAccessMessage">OK</x-button>
        </div>
    </x-modal>
</template>

<script>
    import xButton from '../../axons/inputs/Button.vue'
    import xModal from '../../axons/popover/Modal.vue'

    export default {
        name: 'x-access-modal',
        components: {xButton, xModal},
        props: {value: {}},
        methods: {
            dismissAccessMessage() {
                this.$emit('input', '')
            }
        }
    }
</script>

<style lang="scss">

</style>