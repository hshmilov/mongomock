<template>
    <div class="x-cross">
        <div class="first"></div>
        <div class="second"></div>
    </div>
</template>

<script>
    export default {
        name: 'x-cross'
    }
</script>

<style lang="scss">
    .x-cross {
        position: relative;
        height: 16px;
        width: 16px;

        .first, .second {
            width: 2px;
            height: 16px;
            border-left: 1px solid;
            position: absolute;
            top: 0;
            left: 8px;
        }

        .first {
            transform: rotate(135deg);
            left: 7px;
        }

        .second {
            transform: rotate(45deg);
        }
    }
</style>