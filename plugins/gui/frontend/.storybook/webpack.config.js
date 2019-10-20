const path = require('path')
const webpack = require('webpack')
// Export a function. Accept the base config as the only param.
module.exports = async ({ config, mode }) => {
  // `mode` has a value of 'DEVELOPMENT' or 'PRODUCTION'
  // You can change the configuration based on that.
  // 'PRODUCTION' is used when building the static version of storybook.

  // Make whatever fine-grained changes you need
  config.module.rules.push({
    test: /\.(sa|sc|c)ss$/,
    use: [
        'vue-style-loader',
        {
            loader: 'css-loader',
            options: {
                url: false
            }
        },
        'sass-loader',
        {
            loader: 'sass-resources-loader',
            options: {
                resources: path.resolve(__dirname, '../src/assets/scss/config.scss')
            }
        },
        {
            loader: 'sass-resources-loader',
            options: {
                resources: path.resolve(__dirname, '../src/assets/scss/custom_config.scss')
            }
        }
    ]
});

// Add plugins:
config.plugins.push(new webpack.DefinePlugin({
    ENV: {
        medical: false
    }
}))

  // Return the altered config
  return config;
};