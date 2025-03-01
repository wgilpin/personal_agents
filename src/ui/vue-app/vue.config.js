module.exports = {
  publicPath: './',
  outputDir: 'dist',
  assetsDir: 'assets',
  devServer: {
    port: 8080,
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
