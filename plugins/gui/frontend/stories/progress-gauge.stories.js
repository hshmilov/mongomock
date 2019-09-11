import Vue from 'vue'
import { withKnobs, text, boolean, number } from '@storybook/addon-knobs'
import { gettingStarted, storiesOfAxons } from './index.stories';

storiesOfAxons.add('ProgressGauge', () => ({
        props: {
            color: {default: text('color', '#2db67c')},
            background: {default: boolean('background', true)},
            steps: {default: number('steps', 7)},
            progress: {default: number('progress', 5)},
        },
        template: `<x-progress-gauge :radius="45" :color="color" :strok="3" :background="background" :steps="steps" :progress="progress"/>`
    })
)

gettingStarted.add('ProgressGauge - comleted', () => ({
        template: `<x-progress-gauge :radius="45" background :steps="7" :progress="7"/>`
    })
)

gettingStarted.add('ProgressGauge - empty', () => ({
    template: `<x-progress-gauge :radius="45" background :steps="7" :progress="0"/>`
})
)

gettingStarted.add('ProgressGauge - partly', () => ({
    template: `<x-progress-gauge :radius="45" background :steps="7" :progress="4"/>`
})
)

gettingStarted.add('ProgressGauge - no background', () => ({
    template: `<x-progress-gauge :radius="45" :background="false" :steps="7" :progress="5"/>`
})
)