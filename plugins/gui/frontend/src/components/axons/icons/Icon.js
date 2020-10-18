import { Icon as AIcon } from 'ant-design-vue';
import _prop from 'lodash/property';
import _omit from 'lodash/omit';
import _set from 'lodash/set';
import navigation from './navigation';
import custom from './custom';
import symbol from './symbol';
import illustration from './illustration';
import action from './action';
import logo from './logo';

const categories = {
  navigation,
  custom,
  symbol,
  logo,
  illustration,
  action,
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
