<template>
    <div class="x-logo-name">
        <img :src="`/src/assets/images/logos/${name}.png`" height="24">
        <div class="title">{{prettyName}}</div>
    </div>
</template>

<script>
    import { pluginMeta } from '../../static'

	export default {
		name: 'x-logo-name',
        props: { name: {required: true } },
        computed: {
			prettyName() {
				if (pluginMeta[this.name]) {
					return pluginMeta[this.name].title
                }
                return name
            }
        }
	}
</script>

<style lang="scss">
    .x-logo-name {
        display: flex;
        .title {
            margin-left: 8px;
        }
    }
</style>