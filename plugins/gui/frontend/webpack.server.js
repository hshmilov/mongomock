const merge = require('webpack-merge');
const webpack = require('webpack');
const path = require('path');
const common = require('./webpack.common.js');
const antdLessVars = require('./src/assets/less/antd-less-vars.json');

module.exports = (env) => merge(common(env), {
  mode: 'development',
  module: {
    rules: [
      {
        test: /\.(sa|sc|c)ss$/,
        use: [
          'vue-style-loader',
          'css-loader',
          'sass-loader',
          {
            loader: 'sass-resources-loader',
            options: {
              resources: path.resolve(__dirname, './src/assets/scss/config.scss'),
            },
          },
        ],
      },
      {
        test: /\.less$/,
        use: [{
          loader: 'style-loader',
        }, {
          loader: 'css-loader',
        }, {
          loader: 'less-loader',
          options: {
            modifyVars: antdLessVars,
            javascriptEnabled: true,
          },
        }],
      },
    ],
  },
  devtool: 'inline-source-map',
  devServer: {
    contentBase: './',
    hot: true,
    historyApiFallback: true,
  },
  plugins: [
    new webpack.HotModuleReplacementPlugin(),
  ],
  output: {
    filename: 'build.js',
    publicPath: '/',
  },
});
