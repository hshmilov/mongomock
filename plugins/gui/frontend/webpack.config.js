/* eslint-disable no-undef */
const VueLoaderPlugin = require('vue-loader/lib/plugin')
const HtmlWebpackPlugin = require('html-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const autoprefixer = require('autoprefixer')
const path = require('path')
const webpack = require('webpack')
const devMode = process.env.NODE_ENV !== 'production'

module.exports = {
    entry: './src/main.js',
    output: {
        path: path.resolve(__dirname, './dist'),
        publicPath: '/dist/',
        filename: devMode ? 'build.js' : 'build.[contenthash].js'
    },
    module: {
        rules: [
            {
                test: /\.js$/,
                loader: 'babel-loader',
                exclude: /node_modules/
            },
            {
                test: /\.vue$/,
                loader: 'vue-loader',
                options: {
                    preserveWhitespace: false,
                    postcss: [
                        autoprefixer({
                            browsers: ['last 7 versions']
                        })
                    ]
                }
            },
            {
                test: /\.(sa|sc|c)ss$/,
                use: [
                    MiniCssExtractPlugin.loader,
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
                            resources: path.resolve(__dirname, './src/scss/config.scss')
                        }
                    },
                    {
                        loader: 'sass-resources-loader',
                        options: {
                            resources: path.resolve(__dirname, './src/scss/custom_config.scss')
                        }
                    }
                ]
            },
            {
                test: /\.(png|jpg|gif|svg|woff2?|eot|ttf)(\?v=[0-9\.]+)?$/,
                loader: 'file-loader',
                options: {
                    name: '[name].[ext]?[hash]'
                }
            }
        ]
    },
    optimization: {
        runtimeChunk: 'single',
        splitChunks: {
            cacheGroups: {
                vendor: {
                    test: /[\\/]node_modules[\\/]/,
                    name: 'vendors',
                    chunks: 'all'
                },
                styles: {
                    name: 'styles',
                    test: /\.css$/,
                    chunks: 'all',
                    enforce: true
                }
            }

        }
    },
    resolve: {
        alias: {
            'vue$': 'vue/dist/vue.esm.js',
            Logos: path.resolve(__dirname, '../../../axonius-libs/src/libs/axonius-py/axonius/assets/logos/')
        }
    },
    devServer: {
        historyApiFallback: true,
        noInfo: true
    },
    performance: {
        hints: false
    },
    devtool: devMode ? '#eval-source-map' : '',
    plugins: [
        new VueLoaderPlugin(),
        new HtmlWebpackPlugin({
            hash: true,
            template: __dirname + '/index.html',
            filename: __dirname + '/dist/index.html'
        }),
        new MiniCssExtractPlugin({
            path: path.resolve(__dirname, './dist'),
            publicPath: '/dist/',
            filename: devMode ? '[name].css' : '[name].[contenthash].css'
        }),
        autoprefixer
    ]
}

if (!devMode) {
    module.exports.plugins = (module.exports.plugins || []).concat([
        new webpack.LoaderOptionsPlugin({
            minimize: true
        }),
        new webpack.IgnorePlugin(/^\.\/locale/)
    ])
}
