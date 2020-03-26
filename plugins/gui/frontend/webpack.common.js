const webpack = require('webpack');
const path = require('path');
const { VueLoaderPlugin } = require('vue-loader');
const CleanWebpackPlugin = require('clean-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
// import AntdDayjsWebpackPlugin from 'antd-dayjs-webpack-plugin';

module.exports = (env) => ({
  entry: {
    main: path.resolve(__dirname, 'src/main.js'),
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.vue$/,
        loader: 'vue-loader',
        options: {
          preserveWhitespace: false,
        },
      },
      {
        test: /\.(png|jpg|gif|svg|woff2?|eot|ttf)(\?v=[0-9\.]+)?$/,
        loader: 'file-loader',
        options: {
          name: '[name].[ext]',
        },
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
            modifyVars: {
              'primary-color': '#0076FF',
              'btn-height-base': '30px',
            },
            javascriptEnabled: true,
          },
        }],
      },
    ],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@components': path.resolve(__dirname, 'src/components'),
      '@axons': path.resolve(__dirname, 'src/components/axons'),
      '@networks': path.resolve(__dirname, 'src/components/networks'),
      '@neurons': path.resolve(__dirname, 'src/components/neurons'),
      '@pages': path.resolve(__dirname, 'src/components/pages'),
      '@api': path.resolve(__dirname, 'src/api'),
      '@store': path.resolve(__dirname, 'src/store'),
      '@constants': path.resolve(__dirname, 'src/constants'),
      vue$: 'vue/dist/vue.esm.js',
      Logos: path.resolve(__dirname, '../../../axonius-libs/src/libs/axonius-py/axonius/assets/logos/'),
    },
  },
  plugins: [
    new webpack.IgnorePlugin(/node_modules\/ant-design-vue\/lib\/style\/core\/base\.less/),
    // new AntdDayjsWebpackPlugin(),
    new VueLoaderPlugin(),
    new CleanWebpackPlugin(['dist']),
    new HtmlWebpackPlugin({
      template: `${__dirname}/index.html`,
    }),
    new webpack.DefinePlugin({
      ENV: {
        client: env ? JSON.stringify(env.client) : undefined,
      },
    }),
  ],
  stats: {
    modules: true,
    warnings: true,
    children: false,
  },
});
