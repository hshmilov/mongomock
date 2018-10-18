<template>
    <div class="x-logo-name" :id="name">
        <img :src="`/src/assets/images/logos/${name}.png`" height="24" class="md-image">
        <div class="title">{{ prettyName }}</div>
    </div>
</template>

<script>
    import { pluginMeta } from '../../constants/plugin_meta'

	export default {
		name: 'x-logo-name',
        props: { name: { required: true }, title: { } },
        computed: {
			prettyName() {
			    if (this.title) return this.title
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
        align-items: center;
        .title {
            margin-left: 8px;
            white-space: nowrap;
        }
    }
</style>