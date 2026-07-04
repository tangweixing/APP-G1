module.exports = {
  devServer: {
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://192.168.4.53:5000',
        changeOrigin: true,
        proxyTimeout: 300000,
        timeout: 300000
      },
      '/socket.io': {
        target: 'http://192.168.4.53:5000',
        changeOrigin: true,
        ws: true,
        proxyTimeout: 300000,
        timeout: 300000
      }
    }
  }
}
