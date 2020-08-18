const chartColorsPreset = [
  '#D3D7DA',
  '#096DD9',
  '#8ABA11',
  '#FFD666',
  '#EB7AD0',
  '#003A8B',
  '#43AA8A',
  '#324353',
  '#5B8C00',
  '#9254DE',
];
// eslint-disable-next-line import/prefer-default-export
const intersectingColorsBase = [chartColorsPreset[1], chartColorsPreset[2]];
const defaultChartsColors = {
  segmentation: chartColorsPreset,
  pieColors: chartColorsPreset,
  matrixColor: [...intersectingColorsBase, chartColorsPreset[3]],
  lineColors: [...intersectingColorsBase, chartColorsPreset[3]],
  intersectingColors: intersectingColorsBase,
};

export default defaultChartsColors;
