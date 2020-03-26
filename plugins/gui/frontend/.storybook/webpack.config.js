const path = require('path')
const webpack = require('webpack')

// Export a function. Accept the base config as the only param.
module.exports = async ({ config }, env) => {

  // Make whatever fine-grained changes you need
  config.module.rules = config.module.rules
    .concat([{
      test: /\.s(a|c)ss$/,
      use: [
        'vue-style-loader',
        'css-loader',
        'sass-loader',
        {
            loader: 'sass-resources-loader',
            options: {
                resources: path.resolve(__dirname, '../src/assets/scss/config.scss')
            }
        }
      ]
    }, {
      test: /\.js$/,
      loader: 'babel-loader',
      exclude: /node_modules/
    }, {
      test: /\.(png|jpg|gif|svg|woff2?|eot|ttf)(\?v=[0-9\.]+)?$/,
      loader: 'file-loader',
      options: {
        name: '[name].[ext]'
      }
    }]);

  // Add plugins:
  config.plugins.push(new webpack.DefinePlugin({
    ENV: {
      client: env ? JSON.stringify(env.client) : undefined
    }
  }));

  config.resolve.alias = {
    ...config.resolve.alias,
    Logos: path.resolve(__dirname, '../../../../axonius-libs/src/libs/axonius-py/axonius/assets/logos/')
  };

  // Return the altered config
  return config;
};