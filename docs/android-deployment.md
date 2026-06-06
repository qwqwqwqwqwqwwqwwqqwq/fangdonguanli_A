# Android 移动端部署指南

## 三种部署方式

| 方式 | 适用场景 | 复杂度 |
|------|----------|--------|
| 1. 手机浏览器访问 | 开发调试 | ⭐ |
| 2. PWA (添加到桌面) | 快速分发给租客 | ⭐⭐ |
| 3. Capacitor 打包 APK | 正式发布 | ⭐⭐⭐ |

---

## 方式1: 手机浏览器访问（开发调试）

### 1.1 启动开发服务器

```bash
cd frontend
npm run dev
# → http://localhost:5173
```

### 1.2 手机连接

**条件**: 手机和电脑在同一局域网（同一 WiFi）

```bash
# 查看电脑 IP
ipconfig          # Windows
ifconfig          # Linux/Mac

# 手机浏览器访问
http://你的电脑IP:5173
```

> ⚠️ 确保防火墙允许 5173 端口入站连接

### 1.3 ADB 端口转发（USB 连接）

```bash
# 将手机的 8080 端口转发到电脑的 5173
adb reverse tcp:8080 tcp:5173

# 手机浏览器访问
http://localhost:8080
```

---

## 方式2: PWA 安装（推荐快速分发）

### 2.1 构建生产版本

```bash
cd frontend
npm run build          # 输出到 dist/
```

### 2.2 部署到静态服务器

```bash
# 方式A: 使用 vite preview
npx vite preview --host 0.0.0.0 --port 4173

# 方式B: 使用 Python HTTP Server (部署到手机)
# 将 dist/ 目录复制到手机
adb push dist/ /sdcard/landlord-app/
# 手机上用 HTTP Server 类 APP 打开（如 Simple HTTP Server）
```

### 2.3 在 Android 上安装 PWA

1. Chrome 打开应用 URL
2. 点击地址栏右侧的 **⋮ → 添加到主屏幕**
3. 填写名称 → **添加**
4. 桌面出现"房东管家"图标，点击即可以独立 APP 形式打开

**PWA 特性**:
- ✅ 独立窗口（无浏览器地址栏）
- ✅ 离线服务（Service Worker 缓存）
- ✅ 桌面图标
- ✅ 全屏沉浸式体验
- ✅ 自动更新提示

---

## 方式3: Capacitor 打包 APK

### 3.1 前置要求

安装 Android Studio 和 JDK 17+：

```bash
# 设置环境变量
set ANDROID_HOME=C:\Users\你的用户名\AppData\Local\Android\Sdk     # Windows
export ANDROID_HOME=~/Android/Sdk                                    # Linux/Mac

# 将以下加入 PATH:
# %ANDROID_HOME%\platform-tools
# %ANDROID_HOME%\cmdline-tools\latest\bin
```

### 3.2 初始化 Capacitor

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 生成图标
python generate-icons.py

# 3. 构建前端
npm run build

# 4. 初始化 Capacitor Android 平台
npx cap add android
# → 生成 android/ 目录

# 5. 同步 web 资源到 Android
npx cap sync android
```

### 3.3 配置 Android

在 `android/app/src/main/AndroidManifest.xml` 中确保：

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<application
    android:usesCleartextTraffic="true"
    ...>
    <activity
        android:configChanges="orientation|keyboardHidden|keyboard|screenSize|locale|smallestScreenSize|screenLayout|uiMode"
        ...>
    </activity>
</application>
```

### 3.4 配置状态栏颜色

在 `android/app/src/main/res/values/styles.xml`:

```xml
<resources>
    <style name="AppTheme" parent="Theme.AppCompat.Light.NoActionBar">
        <item name="colorPrimary">#1989fa</item>
        <item name="colorPrimaryDark">#1476d6</item>
        <item name="colorAccent">#1989fa</item>
    </style>
</resources>
```

### 3.5 构建 APK

```bash
# 方式A: 命令行构建 debug APK
cd android
./gradlew assembleDebug
# → android/app/build/outputs/apk/debug/app-debug.apk

# 方式B: Android Studio 打开 android/ 目录
# Build → Build Bundle(s)/APK(s) → Build APK(s)

# 方式C: 一键构建
npm run cap:build
```

### 3.6 安装到手机

```bash
# ADB 安装
adb install android/app/build/outputs/apk/debug/app-debug.apk

# 或直接复制到手机手动安装
adb push android/app/build/outputs/apk/debug/app-debug.apk /sdcard/Download/
```

### 3.7 开发调试

```bash
# 1. 修改 capacitor.config.ts 启用开发服务器
# 取消注释 server.url 指向你的开发服务器

# 2. 启动开发服务器
npm run dev

# 3. 同步并重新构建
npx cap sync android
cd android && ./gradlew assembleDebug

# 4. Chrome DevTools 远程调试
# chrome://inspect → 选择设备 → inspect
```

---

## 移动端优化清单

### 已实现

- [x] `viewport-fit=cover` 全面屏适配
- [x] `env(safe-area-inset-*)` 安全区域 CSS 变量
- [x] `-webkit-tap-highlight-color: transparent` 去除点击高亮
- [x] `overscroll-behavior: none` 禁止橡皮筋效果
- [x] `manifest.json` PWA 配置
- [x] Service Worker 离线缓存
- [x] 7 种尺寸 PWA 图标 (48-512px)
- [x] X5 浏览器兼容 meta 标签
- [x] 电话号检测禁用 (`format-detection`)
- [x] `user-scalable=no` 禁止缩放
- [x] Vant Tabbar 安全区域适配
- [x] hardware back button 处理
- [x] Capacitor 配置 (StatusBar, SplashScreen)

### 建议后续优化

- [ ] 添加下拉刷新 (van-pull-refresh)
- [ ] 图片懒加载 (van-lazyload)
- [ ] 推送通知 (FCM / 极光推送)
- [ ] 微信/支付宝 SDK 集成
- [ ] 深色模式支持
- [ ] 多语言支持
- [ ] 无障碍访问 (TalkBack)
- [ ] 启动屏自定义设计

---

## 常见问题

| 问题 | 解决 |
|------|------|
| APK 安装后闪退 | 检查 `AndroidManifest.xml` 中 `INTERNET` 权限 |
| 无法连接后端 | 确保 `capacitor.config.ts` 中 `server.url` 指向正确地址 |
| PWA 无法安装 | 检查 HTTPS + manifest.json + SW + 图标 是否齐全 |
| 图标不显示 | 检查 `public/icons/` 中 PNG 文件是否存在 |
| 构建报错 | 确保 `ANDROID_HOME` 和 JDK 17+ 环境变量正确 |
| Gradle 下载慢 | 使用阿里云镜像：`build.gradle` 中配置 `maven { url 'https://maven.aliyun.com/repository/google' }` |
