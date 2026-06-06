<template>
  <div id="app-root">
    <router-view v-slot="{ Component }">
      <keep-alive>
        <component :is="Component" />
      </keep-alive>
    </router-view>
    <van-tabbar route v-model="active" :fixed="true" :border="true" :safe-area-inset-bottom="true">
      <van-tabbar-item to="/" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/contracts" icon="description-o">合同</van-tabbar-item>
      <van-tabbar-item to="/bills" icon="balance-o">账单</van-tabbar-item>
      <van-tabbar-item to="/properties" icon="shop-o">房产</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const active = ref(0)

watch(() => route.path, (path) => {
  if (path === '/' || path.startsWith('/home')) active.value = 0
  else if (path.startsWith('/contracts')) active.value = 1
  else if (path.startsWith('/bills') || path.startsWith('/payments')) active.value = 2
  else if (path.startsWith('/properties')) active.value = 3
  else if (path.startsWith('/tenants') || path.startsWith('/meter-readings')) active.value = -1
  else active.value = -1
}, { immediate: true })
</script>
