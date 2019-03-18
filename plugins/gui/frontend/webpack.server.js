const merge = require('webpack-merge');
const common = require('./webpack.common.js');

const webpack = require('webpack');
const path = require('path');

module.exports = env => {
    return merge(common(env), {
        mode: 'development',
        module: {
            rules: [
                {
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
                                resources: path.resolve(__dirname, './src/assets/scss/config.scss')
                            }
                        },
                        {
                            loader: 'sass-resources-loader',
                            options: {
                                resources: path.resolve(__dirname, './src/assets/scss/custom_config.scss')
                            }
                        }
                    ]
                }
            ]
        },
        devtool: 'inline-source-map',
        devServer: {
            contentBase: './',
            hot: true,
            historyApiFallback: true
        },
        plugins: [
            new webpack.HotModuleReplacementPlugin(),
        ],
        output: {
            filename: 'build.js',
            publicPath: '/'
        }
    });
}