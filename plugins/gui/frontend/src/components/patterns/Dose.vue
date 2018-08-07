<template>
    <svg height="48px" viewBox="0 0 512 820" class="x-dose" :class="{placeholder: placeholder}">
        <defs>
            <linearGradient y2="0%" x2="0%" y1="100%" x1="0%" :id="`fill-${percentage}`">
                <stop class="svg-stop" :offset="`${percentage}%`" v-if="percentage" />
                <stop stop-color="#FFFFFF" offset="0%" />
            </linearGradient>
        </defs>
        <g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd" transform="translate(0.000000, 8.000000)">
            <rect class="svg-stroke" x="8" y="64.3811802" width="496" height="500" rx="64" stroke-width="24"
                  :fill="`url(#fill-${percentage})`"></rect>
            <rect fill="#FFFFFF" x="36" y="189.368421" width="240" height="36" rx="8"></rect>
            <rect fill="#FFFFFF" x="36" y="270.389155" width="240" height="36" rx="8"></rect>
            <rect fill="#FFFFFF" x="36" y="351.409888" width="240" height="36" rx="8"></rect>
            <rect fill="#FFFFFF" x="36" y="432.430622" width="240" height="36" rx="8"></rect>
            <path stroke-width="24" d="M194,64 C198.253372,41.8403306 203.032039,27.4089581 208.336,20.7058824 C224.72,0 245.2,7.83773951e-16 258,0 C270.8,0 291.28,0 307.664,20.7058824 C312.636741,26.9903662 317.415407,41.4217387 322,64" class="svg-stroke"></path>
            <path stroke-width="24" d="M206,597.370016 C209.322947,586.767303 213.05628,579.86234 217.2,576.655127 C230,566.748006 246,566.748006 256,566.748006 C266,566.748006 282,566.748006 294.8,576.655127 C298.684954,579.662057 302.418287,586.56702 306,597.370016 L206,597.370016 Z" class="svg-stroke svg-fill" transform="translate(256.000000, 582.059011) scale(1, -1) translate(-256.000000, -582.059011) "></path>
            <path stroke-width="24" d="M254,595.370016 C236,599.623073 221.333333,604.088783 210,608.767145 C193,615.784689 185,623.767262 185,635.561404 C185,647.355545 190.690915,653.429288 210,662.355662 C229.309085,671.282036 241,673.838915 254,678.942584 C267,684.046252 277,688.511962 291,695.529506 C305,702.547049 325,714.030303 325,724.875598 C325,735.720893 306.260532,746.016316 291,751.669856 C278.722221,756.218382 255,770.170654 254,781.653907 C253.743042,784.604624 253.743042,794.386655 254,811" class="svg-stroke"></path>
        </g>
    </svg>
</template>

<script>
	export default {
		name: 'x-dose',
        props: { percentage: { default: 0 }, placeholder: { } }
	}
</script>

<style lang="scss">
    .x-dose {
        .svg-stroke {
            stroke: $theme-blue;
        }
        .svg-fill {
            fill: $theme-blue;
        }
        .svg-stop {
            stop-color: $theme-blue;
        }
        &.placeholder {
            .svg-stroke {
                stroke: $grey-3;
                stroke-dasharray: 48
            }
            .svg-fill {
                fill: $grey-3;
            }
        }
    }
</style>