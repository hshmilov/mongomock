export const isTooDark = (hexcolor) => {
  const r = parseInt(hexcolor.substr(1, 2), 16);
  const g = parseInt(hexcolor.substr(3, 2), 16);
  const b = parseInt(hexcolor.substr(4, 2), 16);
  const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
  return (yiq < 150);
};

export const getVisibleTextColor = (backgroudHexColor) => (isTooDark(backgroudHexColor) ? '#fff' : '#1D222C');
