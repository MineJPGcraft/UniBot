import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, KeepAlive, nextTick, ref } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'

/**
 * AppLayout 的路由缓存策略依赖两个框架行为，任一变化都会让缓存静默失效：
 * 1. `<script setup>` 编译出的 `__name` 能匹配 KeepAlive 的 include；
 * 2. vue-router 在导航守卫阶段把懒加载路由组件解析为组件对象，
 *    因此 RouterView 渲染的是「带 __name 的组件」而非未解析的加载函数。
 * 本测试用与 AppLayout 相同的结构（RouterView + transition + KeepAlive include）验证这两点。
 */

/** 统计挂载次数的页面组件（模拟数据稳定页） */
function make_view(name) {
  const counts = { mounted: 0 }
  const view = defineComponent({
    name,
    setup() {
      counts.mounted += 1
      return () => h('div', { class: 'view' }, name)
    },
  })
  return { view, counts }
}

describe('KeepAlive 按组件名缓存懒加载路由页面', () => {
  it('缓存页离开后重新进入不重新挂载，非缓存页重新挂载', async () => {
    const cached = make_view('DashboardView')
    const uncached = make_view('LogsView')

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        // 与真实项目一致：懒加载，组件定义来自异步 import
        { path: '/', name: 'DashboardView', component: () => Promise.resolve(cached.view) },
        { path: '/logs', name: 'LogsView', component: () => Promise.resolve(uncached.view) },
      ],
    })

    const KEEP_ALIVE_VIEWS = ['DashboardView']
    const host = mount(
      defineComponent({
        setup() {
          return () =>
            h(RouterView, null, {
              default: ({ Component }) =>
                h(KeepAlive, { include: KEEP_ALIVE_VIEWS }, { default: () => h(Component) }),
            })
        },
      }),
      { global: { plugins: [router] } },
    )

    router.push('/')
    await router.isReady()
    await nextTick()
    expect(host.find('.view').text()).toBe('DashboardView')
    expect(cached.counts.mounted).toBe(1)

    await router.push('/logs')
    await nextTick()
    await nextTick()
    expect(host.find('.view').text()).toBe('LogsView')

    await router.push('/')
    await nextTick()
    await nextTick()
    expect(host.find('.view').text()).toBe('DashboardView')
    // 关键断言：命中 include 的页面复用缓存实例
    expect(cached.counts.mounted).toBe(1)

    await router.push('/logs')
    await nextTick()
    await nextTick()
    // 未命中 include 的页面每次重新挂载
    expect(uncached.counts.mounted).toBe(2)
  })

  it('被缓存页面的 onActivated 会随重新进入触发（供静默刷新使用）', async () => {
    const activated = ref(0)
    const view = defineComponent({
      name: 'StatisticsView',
      activated() {
        activated.value += 1
      },
      setup() {
        return () => h('div', { class: 'view' }, 'StatisticsView')
      },
    })
    const other = defineComponent({ name: 'OtherView', setup: () => () => h('div', 'Other') })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'StatisticsView', component: () => Promise.resolve(view) },
        { path: '/other', name: 'OtherView', component: () => Promise.resolve(other) },
      ],
    })

    const host = mount(
      defineComponent({
        setup() {
          return () =>
            h(RouterView, null, {
              default: ({ Component }) =>
                h(KeepAlive, { include: ['StatisticsView'] }, { default: () => h(Component) }),
            })
        },
      }),
      { global: { plugins: [router] } },
    )

    router.push('/')
    await router.isReady()
    await nextTick()
    expect(host.find('.view').text()).toBe('StatisticsView')
    // 注意：KeepAlive 下首次挂载也会触发 activated（Vue 既定行为），
    // 因此视图内的「切回才刷新」必须自己用一次性标志跳过首次
    expect(activated.value).toBe(1)

    await router.push('/other')
    await nextTick()
    await nextTick()
    await router.push('/')
    await nextTick()
    await nextTick()
    expect(host.find('.view').text()).toBe('StatisticsView')
    // 切回后实例复用（onMounted 不再触发），onActivated 是刷新的唯一入口
    expect(activated.value).toBe(2)
  })
})
