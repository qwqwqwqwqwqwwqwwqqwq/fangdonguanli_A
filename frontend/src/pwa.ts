// 房东管家 - PWA 注册 + Capacitor 初始化
// 仅在浏览器环境下注册 Service Worker
export function registerSW() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js', { scope: '/' })
        .then((reg) => {
          console.log('[PWA] Service Worker 已注册:', reg.scope)
          // 监听更新
          reg.addEventListener('updatefound', () => {
            const newWorker = reg.installing
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  console.log('[PWA] 新版本可用，请刷新页面')
                  // 可触发更新提示
                  window.dispatchEvent(new CustomEvent('sw-update-available'))
                }
              })
            }
          })
        })
        .catch((err) => {
          console.warn('[PWA] Service Worker 注册失败:', err)
        })
    })
  }
}

// Android 返回键处理（在 WebView 或 PWA 中）
export function setupAndroidBackButton(_router: any) {
  // 监听 popstate（Android 返回键和浏览器后退触发）
  window.addEventListener('popstate', (_e) => {
    // hash 路由自动处理，此处仅记录
    console.log('[Android] 返回键触发')
  })

  // Capacitor App 插件（如果在 Capacitor 环境中）
  if (typeof (window as any).Capacitor !== 'undefined') {
    import('@capacitor/app').then(({ App: CapacitorApp }) => {
      CapacitorApp.addListener('backButton', ({ canGoBack }: { canGoBack: boolean }) => {
        if (!canGoBack) {
          // 根路由：提示退出
          if (confirm('确定要退出房东管家吗？')) {
            CapacitorApp.exitApp()
          }
        } else {
          // 非根路由：正常返回
          window.history.back()
        }
      })
    }).catch((e) => {
      console.log('[Capacitor] App 插件未安装，使用浏览器默认行为', e)
    })
  }
}

// 状态栏配置（用于 Capacitor StatusBar 插件）
export function setupStatusBar() {
  if (typeof (window as any).Capacitor !== 'undefined') {
    import('@capacitor/status-bar').then(({ StatusBar, Style }) => {
      StatusBar.setStyle({ style: Style.Dark })
      StatusBar.setBackgroundColor({ color: '#1989fa' })
    }).catch((e) => {
      console.log('[Capacitor] StatusBar 插件未安装', e)
    })
  }
}
