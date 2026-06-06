import { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.landlord.app',
  appName: '房东管家',
  webDir: 'dist',
  server: {
    // 开发时使用本地服务器，打包 APK 时注释掉
    // url: 'http://192.168.1.100:5173',
    // cleartext: true,
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
