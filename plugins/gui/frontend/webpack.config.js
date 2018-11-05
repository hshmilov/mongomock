/* eslint-disable no-undef */
var HtmlWebpackPlugin = require('html-webpack-plugin')
var ExtractTextPlugin = require('extract-text-webpack-plugin')
var autoprefixer = require('autoprefixer')
let path = require('path')
let webpack = require('webpack')

module.exports = {
	entry: './src/main.js',
	output: {
		path: path.resolve(__dirname, './dist'),
		publicPath: '/dist/',
		filename: 'build.js',
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
					postcss: [autoprefixer({browsers: ['last 7 versions']})],
					loaders: {
						scss: ExtractTextPlugin.extract({
							use: [
								{
									loader: 'css-loader',
									options: {
										minimize: process.env.NODE_ENV === 'production',
									}
								},
								{ loader: 'sass-loader' },
								{
									loader: 'sass-resources-loader',
									options: {
										resources: path.resolve(__dirname, './src/scss/config.scss')
									},
								},
								{
									loader: 'sass-resources-loader',
									options: {
										resources: path.resolve(__dirname, './src/scss/custom_config.scss')
									},
								}
							],
							fallback: 'vue-style-loader'
						}),
					}
				}
			},
			{
                test: /\.css$/,
                loader:[ 'vue-style-loader', 'css-loader' ]
			},
			{
				test: /\.(png|jpg|gif|svg|woff2?|eot|ttf)(\?v=[0-9\.]+)?$/,
				loader: 'file-loader',
				options: {
					name: '[name].[ext]?[hash]',
				},
			},
		],
	},
	resolve: {
		alias: {
			'vue$': 'vue/dist/vue.esm.js',
             Logos: path.resolve(__dirname, '../../../axonius-libs/src/libs/axonius-py/axonius/assets/logos/')
		},
	},
	devServer: {
		historyApiFallback: true,
		noInfo: true,
	},
	performance: {
		hints: false,
	},
	devtool: '#eval-source-map',
	plugins: [
		new webpack.DefinePlugin({
			'process.env': {
				NODE_ENV: '"' + process.env.NODE_ENV + '"',
			},
		}),
		new HtmlWebpackPlugin({
			hash: true,
			template: __dirname + '/index.html',
			filename: __dirname + '/dist/index.html',
		}),
		new ExtractTextPlugin('styles.css'),
		autoprefixer
	]
}

if (process.env.NODE_ENV === 'production') {
	module.exports.devtool = ''
	module.exports.plugins = (module.exports.plugins || []).concat([
		new webpack.optimize.UglifyJsPlugin({
			compress: {
				warnings: false,
			},
		}),
		new webpack.LoaderOptionsPlugin({
			minimize: true,
		}),
		new webpack.IgnorePlugin(/^\.\/locale/)
	])
}
