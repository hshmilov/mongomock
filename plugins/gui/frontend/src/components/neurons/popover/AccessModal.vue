<template>
    <x-modal v-if="value" @close="dismissAccessMessage">
        <div slot="body">You do not have permission to access the {{ value }} screen</div>
        <div slot="footer">
            <button class="x-btn" @click="dismissAccessMessage">OK</button>
        </div>
    </x-modal>
</template>

<script>
    import xModal from '../../axons/popover/Modal.vue'

    export default {
        name: 'x-access-modal',
        components: {xModal},
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