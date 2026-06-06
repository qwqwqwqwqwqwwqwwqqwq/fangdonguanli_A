import { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.landlord.app',
  appName: '房东管家',
  webDir: 'dist',
  server: {
    // 热更新：APK 启动时从 GitHub Pages 加载最新前端
    // git push 代码 → Pages 自动更新 → 手机 App 自动获取最新版
    url: 'https://qwqwqwqwqwqwwqwwqqwq.github.io/fangdonguanli_A',
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
