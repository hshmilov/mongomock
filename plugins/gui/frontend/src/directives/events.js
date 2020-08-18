const handleClickOutside = (e, binding, vnode) => {
  e.stopPropagation();
  const { handler, exclude } = binding.value;
  let clickedOnExcludedEl = false;

  if (exclude) {
    exclude.forEach(() => {
      if (!clickedOnExcludedEl && vnode.context.$refs[exclude]) {
        clickedOnExcludedEl = vnode.context.$refs[exclude].contains(
          e.target,
        );
      }
    });
  }
  const openedElementClicked = vnode.elm.contains(e.target);
  if (!openedElementClicked && !clickedOnExcludedEl) {
    handler(e);
  }
};

let clickOutSideHandler;
// eslint-disable-next-line import/prefer-default-export
export const clickOutside = {
  bind(_, binding, vnode) {
    clickOutSideHandler = (e) => handleClickOutside(e, binding, vnode);
    document.addEventListener('click', clickOutSideHandler);
  },
  unbind() {
    document.removeEventListener('click', clickOutSideHandler);
  },
};
