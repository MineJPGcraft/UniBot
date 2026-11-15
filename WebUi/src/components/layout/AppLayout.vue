<script setup>
import { onMounted, onUnmounted } from 'vue'
import { RouterView } from 'vue-router'
import { storeToRefs } from 'pinia'
import Sidebar from './Sidebar.vue'
import TopBar from './TopBar.vue'
import StatusBar from './StatusBar.vue'
import RestartPrompt from './RestartPrompt.vue'
import UpdatePrompt from './UpdatePrompt.vue'
import { useAuthStore } from '@/stores/auth'
import { useStatusStore } from '@/stores/status'
import { use_websocket } from '@/composables/use_websocket'
import { use_locale_refresh } from '@/composables/use_locale_refresh'

/**
 * 需要缓存复用的页面（按组件名匹配，`<script setup>` 由编译器生成 __name）：
 * 数据稳定、进入即拉取列表的只读页；切回时不再重新挂载与请求。
 * 视图内以 `onActivated` 静默刷新，保证缓存期间数据不过期。
 * 不缓存：Config 等长表单页（保留草稿会与"离开即丢弃"的预期冲突）、
 * 详情页（路由参数变化）、含本地输入状态的 Logs / Extensions / Adapters / Plugins。
 */
const KEEP_ALIVE_VIEWS = [
  'DashboardView',
  'ServersView',
  'PlayersView',
  'UsersView',
  'StatisticsView',
]

const auth_store = useAuthStore()
const status_store = useStatusStore()
const { status } = storeToRefs(status_store)
const { connect, disconnect } = use_websocket()

// 界面语言切换后重拉已加载的语言相关数据（配置 schema / 适配器 / 扩展 / 插件等）
use_locale_refresh()

onMounted(() => {
  auth_store.fetch_me().catch((error) => console.warn('fetch_me failed', error))
  status_store.fetch_status().catch((error) => console.warn('fetch_status failed', error))
  status_store.init()
  connect()
})

onUnmounted(() => {
  status_store.dispose()
  disconnect()
})
</script>

<template>
  <div class="app-shell">
    <Sidebar />
    <div class="app-main">
      <TopBar />
      <main class="app-content">
        <RouterView v-slot="{ Component }">
          <!-- KeepAlive：数据稳定的页面切走后保留实例（含滚动位置与已取数据），切回即时显示。
               过渡保持 out-in 但缩短到 150ms（见 main.css 的 .fade-slide-*）：
               out-in 能保证任一时刻只有一个页面在流内，不会把 app-content 的滚动高度顶起来。 -->
          <transition name="fade-slide" mode="out-in">
            <KeepAlive :include="KEEP_ALIVE_VIEWS">
              <component :is="Component" />
            </KeepAlive>
          </transition>
        </RouterView>
      </main>
      <StatusBar />
    </div>
    <RestartPrompt />
    <UpdatePrompt />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.app-content {
  flex: 1;
  overflow-y: auto;
  scrollbar-gutter: stable;
}
</style>
