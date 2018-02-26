var ExtractPlugin = require('extract-text-webpack-plugin');
const MinifyPlugin = require("babel-minify-webpack-plugin");

module.exports = {
  entry: __dirname + '/js/hearth.js',
  output: {
    path: __dirname + '/www',
    filename: 'hearth.js'
  },
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
        use: ExtractPlugin.extract({
          use: "css-loader"
        })
      }
    ]
  },

  plugins: [
      new ExtractPlugin('hearth.css'),
      //new MinifyPlugin()
  ]
};
