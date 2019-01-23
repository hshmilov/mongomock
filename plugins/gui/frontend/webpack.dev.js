const merge = require('webpack-merge');
const prod = require('./webpack.prod.js');

module.exports = merge(prod, {
    mode: 'none',
    devtool: 'inline-source-map',
});