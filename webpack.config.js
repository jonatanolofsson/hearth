const TerserJSPlugin = require('terser-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const OptimizeCSSAssetsPlugin = require('css-minimizer-webpack-plugin');
const webpack = require('webpack');

module.exports = {
  mode: "production",
  entry: __dirname + '/js/hearth.js',
  output: {
    path: __dirname + '/www',
    filename: 'hearth.js'
  },

  optimization: {
    minimizer: [new TerserJSPlugin({}), new OptimizeCSSAssetsPlugin({})],
  },

  plugins: [
    new webpack.DefinePlugin({ 'process.env.NODE_ENV': JSON.stringify('production') }),
    new MiniCssExtractPlugin({ filename: 'hearth.css', }),
    new webpack.SourceMapDevToolPlugin({ exclude: ['popper.js'] }),
  ],

  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
        }
      },
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader'],
      },
    ],
  },
};
