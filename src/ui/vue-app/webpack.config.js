const path = require('path');
const { VueLoaderPlugin } = require('vue-loader');

module.exports = {
  mode: process.env.NODE_ENV === 'production' ? 'production' : 'development',
  devtool: 'source-map',
  entry: './src/main.js',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'js/[name].[contenthash:8].js',
    publicPath: './',
    devtoolModuleFilenameTemplate: info => {
      const resourcePath = info.resourcePath.split('?')[0];
      return `webpack:///${resourcePath}`;
    }
  },
  resolve: {
    extensions: ['.js', '.vue', '.json'],
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  module: {
    rules: [
      {
        test: /\.vue$/,
        loader: 'vue-loader'
      },
      {
        test: /\.js$/,
        loader: 'babel-loader',
        exclude: /node_modules/
      },
      {
        test: /\.css$/,
        use: [
          'vue-style-loader',
          {
            loader: 'css-loader',
            options: {
              sourceMap: true
            }
          }
        ]
      }
    ]
  },
  plugins: [
    new VueLoaderPlugin()
  ],
  // Polyfill for webpack 5 compatibility
  resolve: {
    fallback: {
      global: require.resolve('./webpack-polyfills/global.js'),
      module: require.resolve('./webpack-polyfills/module.js')
    }
  }
};