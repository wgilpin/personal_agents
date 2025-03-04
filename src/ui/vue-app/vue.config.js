module.exports = {
  publicPath: './',
  outputDir: 'dist',
  assetsDir: 'assets',
  configureWebpack: {
    devtool: 'source-map'
  },
  devServer: {
    port: 8081,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': ''
        }
      }
    }
  }
};
