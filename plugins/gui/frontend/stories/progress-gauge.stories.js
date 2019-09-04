import Vue from 'vue'
import { withKnobs, text, boolean, number } from '@storybook/addon-knobs'
import { stories } from './index.stories';

stories.add('ProgressGauge', () => ({
        props: {
            color: {default: text('color', '#2db67c')},
            background: {default: boolean('background', true)},
            steps: {default: number('steps', 7)},
            progress: {default: number('progress', 5)},
        },
        template: `<x-progress-gauge :radius="45" :color="color" :strok="3" :background="background" :steps="steps" :progress="progress"/>`
    })
)