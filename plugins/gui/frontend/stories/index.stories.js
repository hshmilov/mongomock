import Vue from 'vue';
import { storiesOf } from '@storybook/vue';
import { withKnobs, text, boolean } from '@storybook/addon-knobs';

export const stories = storiesOf('Story Of Axons', module);

stories.addDecorator(withKnobs);