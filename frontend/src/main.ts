import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import routes from './router'
import { registerSW, setupAndroidBackButton, setupStatusBar } from './pwa'
import 'vant/lib/index.css'
import './style.css'

const app = createApp(App)
app.use(createPinia())

const router = createRouter({ history: createWebHashHistory(), routes })
app.use(router)

// PWA: 注册 Service Worker
registerSW()

// Android: 返回键处理
setupAndroidBackButton(router)

// 状态栏适配
setupStatusBar()

app.mount('#app')
