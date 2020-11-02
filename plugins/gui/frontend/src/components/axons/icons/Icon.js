import { Icon as AIcon } from 'ant-design-vue';
import _prop from 'lodash/property';
import _omit from 'lodash/omit';
import _set from 'lodash/set';

import action from './action';
import custom from './custom';
import illustration from './illustration';
import logo from './logo';
import navigation from './navigation';
import symbol from './symbol';

const categories = {
  action,
  custom,
  illustration,
  logo,
  navigation,
  symbol,
};

export default {
  name: 'XIcon',
  functional: true,
  props: {
    ...AIcon.props,
    family: {
      type: String,
      default: '',
    },
  },
  render(h, { props, listeners, data }) {
    const getCustomSVGIcon = (family, type) => {
      const svgIconLense = _prop(`${family}.${type}`);
      return svgIconLense(categories);
    };
    const createElement = h;
    let newProps = { ...props };
    if (props.family) {
      newProps = _omit(props, 'type');
      _set(newProps, 'component', getCustomSVGIcon(props.family, props.type));
    }
    return createElement(
      AIcon,
      {
        ...data,
        class: [data.staticClass, data.class, 'x-icon'],
        props: { ...newProps },
        on: { ...listeners },
      },
    );
  },
};
