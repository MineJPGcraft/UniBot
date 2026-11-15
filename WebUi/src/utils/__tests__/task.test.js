import { beforeEach, describe, expect, it, vi } from 'vitest'

// 语言包由 i18n 模块加载，测试环境注入最小实现（task.js 仅依赖 t_global）
vi.mock('@/i18n', () => ({
  t_global: (key, params) => {
    if (key === 'task_center.kind_extension_install') return '扩展安装'
    if (key === 'task_center.kind_adapter_install') return '适配器安装'
    if (key === 'task_center.kind_unknown') return '后台任务'
    if (key === 'task_center.status_running') return '执行中'
    if (key === 'task_center.status_failed') return '失败'
    if (key === 'task_center.title_extension') return `扩展 ${params?.name}`
    if (key === 'task_center.title_adapter') return `适配器 ${params?.name}`
    if (key === 'task_center.title_package') return `依赖 ${params?.packages}`
    if (key === 'task_center.msg_downloading_extension') return `正在下载扩展 ${params?.name}…`
    // 未命中的键按 vue-i18n 行为回显键名，用于验证回退分支
    return key
  },
}))

const {
  ACTIVE_STATUSES,
  STATUS_VARIANTS,
  format_elapsed,
  is_active,
  kind_icon,
  kind_label,
  status_label,
  status_variant,
  task_elapsed_seconds,
  task_message,
  task_title,
} = await import('@/utils/task')

describe('STATUS_VARIANTS / status_variant', () => {
  it('覆盖全部任务状态', () => {
    expect(Object.keys(STATUS_VARIANTS).sort()).toEqual([
      'cancelled',
      'failed',
      'pending',
      'running',
      'succeeded',
    ])
  })

  it('未知状态回退中性色', () => {
    expect(status_variant('running')).toBe('accent')
    expect(status_variant('unknown')).toBe('neutral')
    expect(status_variant(undefined)).toBe('neutral')
  })
})

describe('is_active', () => {
  it('仅 pending / running 视为活跃', () => {
    expect(is_active({ status: 'pending' })).toBe(true)
    expect(is_active({ status: 'running' })).toBe(true)
    expect(is_active({ status: 'succeeded' })).toBe(false)
    expect(is_active(null)).toBe(false)
  })

  it('活跃集合与状态变体一致', () => {
    expect([...ACTIVE_STATUSES]).toEqual(['pending', 'running'])
  })
})

describe('kind_icon / kind_label', () => {
  it('已知类型返回专属图标', () => {
    expect(kind_icon('extension_install')).toBe('lucide:puzzle')
  })

  it('未知类型回退旋转图标', () => {
    expect(kind_icon('whatever')).toBe('lucide:loader')
  })

  it('语言键缺失时回退「后台任务」', () => {
    expect(kind_label('extension_install')).toBe('扩展安装')
    expect(kind_label('not_a_kind')).toBe('后台任务')
  })
})

describe('status_label', () => {
  it('已翻译返回译文，未翻译回退原状态', () => {
    expect(status_label('running')).toBe('执行中')
    expect(status_label('weird')).toBe('weird')
  })
})

describe('task_title', () => {
  it('带 name 参数且类型匹配前缀时用专属标题模板', () => {
    expect(task_title({ kind: 'extension_install', title_params: { name: 'Performance' } })).toBe(
      '扩展安装 · 扩展 Performance',
    )
  })

  it('插件 / 适配器类型用对应标题模板', () => {
    expect(task_title({ kind: 'adapter_install', title_params: { name: 'QQ' } })).toBe(
      '适配器安装 · 适配器 QQ',
    )
  })

  it('无 name 但带 packages 时用依赖模板', () => {
    expect(task_title({ kind: 'dependency_sync', title_params: { packages: 'a, b' } })).toBe(
      '后台任务 · 依赖 a, b',
    )
  })

  it('无任何参数时仅返回类型名', () => {
    expect(task_title({ kind: 'dependency_sync' })).toBe('后台任务')
  })
})

describe('task_message', () => {
  it('message_key 存在且可翻译时返回译文', () => {
    expect(
      task_message({
        status: 'running',
        message_key: 'task_center.msg_downloading_extension',
        message_params: { name: 'X' },
      }),
    ).toBe('正在下载扩展 X…')
  })

  it('message_key 缺失时回退状态名', () => {
    expect(task_message({ status: 'running' })).toBe('执行中')
  })

  it('message_key 无法翻译时回退状态名（不回显键名）', () => {
    expect(task_message({ status: 'failed', message_key: 'task_center.msg_unknown' })).toBe('失败')
  })
})

describe('task_elapsed_seconds / format_elapsed', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-06T00:00:00Z'))
  })

  it('已结束任务用时为开始到结束', () => {
    expect(task_elapsed_seconds({ started_at: 100, finished_at: 130 })).toBe(30)
  })

  it('未结束任务按当前时刻实时计算', () => {
    const now_seconds = Date.now() / 1000
    expect(task_elapsed_seconds({ started_at: now_seconds - 12 })).toBe(12)
  })

  it('缺失开始时间返回 0，结束早于开始不返回负数', () => {
    expect(task_elapsed_seconds({})).toBe(0)
    expect(task_elapsed_seconds({ started_at: 200, finished_at: 100 })).toBe(0)
  })

  it('耗时格式化：秒 / 分 / 时', () => {
    expect(format_elapsed(0)).toBe('')
    expect(format_elapsed(45)).toBe('45s')
    expect(format_elapsed(65)).toBe('1m 5s')
    expect(format_elapsed(3600 + 20 * 60)).toBe('1h 20m')
  })
})
