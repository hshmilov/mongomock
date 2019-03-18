const merge = require('webpack-merge');
const prod = require('./webpack.prod.js');

module.exports = env => {
    return merge(prod(env), {
        mode: 'none',
        devtool: 'inline-source-map',
    });
}