// 房东管家 - Service Worker (PWA 离线支持)
const CACHE_NAME = 'landlord-v2.0.0'
const RUNTIME_CACHE = 'landlord-runtime'

// 预缓存的静态资源
const PRE_CACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
]

// 安装：预缓存核心资源（容错单个失败）
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      console.log('[SW] 预缓存核心资源')
      const results = await Promise.allSettled(
        PRE_CACHE_URLS.map((url) =>
          cache.add(url).catch((err) => {
            console.warn('[SW] 预缓存失败:', url, err)
          })
        )
      )
      console.log('[SW] 预缓存完成:', results.length, '个资源')
    }).then(() => {
      // 强制新的 SW 立即激活
      return self.skipWaiting()
    })
  )
})

// 激活：清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== RUNTIME_CACHE)
          .map((name) => {
            console.log('[SW] 删除旧缓存:', name)
            return caches.delete(name)
          })
      )
    }).then(() => {
      // 立即接管所有页面
      return self.clients.claim()
    })
  )
})

// 请求：缓存策略 - 网络优先，缓存回退
self.addEventListener('fetch', (event) => {
  // 跳过非 GET 请求和 Chrome 扩展
  if (event.request.method !== 'GET') return
  if (event.request.url.startsWith('chrome-extension://')) return

  // API 请求：网络优先，不缓存
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(JSON.stringify({ error: '网络不可用' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        })
      })
    )
    return
  }

  // 静态资源：缓存优先（Cache First）
  if (
    event.request.url.includes('/assets/') ||
    event.request.url.includes('/icons/') ||
    event.request.destination === 'script' ||
    event.request.destination === 'style' ||
    event.request.destination === 'font' ||
    event.request.destination === 'image'
  ) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached
        return fetch(event.request).then((response) => {
          if (response.ok) {
            const clone = response.clone()
            caches.open(RUNTIME_CACHE).then((cache) => {
              cache.put(event.request, clone)
            })
          }
          return response
        })
      })
    )
    return
  }

  // 其他请求：网络优先，缓存回退
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone()
          caches.open(RUNTIME_CACHE).then((cache) => {
            cache.put(event.request, clone)
          })
        }
        return response
      })
      .catch(() => {
        return caches.match(event.request).then((cached) => {
          return cached || new Response('离线状态，请连接网络后重试', {
            status: 503,
            headers: { 'Content-Type': 'text/plain; charset=utf-8' },
          })
        })
      })
  )
})
