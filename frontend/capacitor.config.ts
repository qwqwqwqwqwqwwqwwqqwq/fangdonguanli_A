import { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.landlord.app',
  appName: '房东管家',
  webDir: 'dist',
  server: {
    // 热更新：APK 启动时从 Render 云端加载最新前端
    // Render 在国内能访问，前端后端在同一服务器
    url: 'https://landlord-api-up06.onrender.com',
    cleartext: false,
    androidScheme: 'https',
  },
  android: {
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: false,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#1989fa',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#1989fa',
    },
  },
}

export default config
