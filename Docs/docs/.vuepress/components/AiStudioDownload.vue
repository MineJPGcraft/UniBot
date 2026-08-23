<template>
  <div class="aistudio-download">
    <table>
      <thead>
        <tr>
          <th>系统</th>
          <th>架构</th>
          <th>安装包</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="option in platformOptions"
          :key="option.fileName"
          :class="{ 'is-current': option === matchedAsset }"
        >
          <td>{{ option.system }}</td>
          <td>{{ option.arch }}</td>
          <td>
            <a :href="downloadUrl(option.fileName)">{{ option.fileName }}</a>
            <span v-if="option === matchedAsset" class="current-tag">（当前系统）</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="detected-line">检测到当前系统：{{ systemText }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

// 与 UniBot 内置 Studio 管理器（Scripts/Managers/Studio.py）保持一致的分发地址
const DOWNLOAD_BASE = 'https://bot-api.mcjpg.dev/files/'

const OS_NAMES = { macos: 'macOS', windows: 'Windows', linux: 'Linux', unknown: '未知系统' }

const platformOptions = [
  {
    system: 'macOS',
    arch: 'Apple Silicon（M 系列）',
    fileName: 'unibot-studio-macos-arm64',
    matches: (os, arch) => os === 'macos' && arch === 'arm64',
  },
  {
    system: 'macOS',
    arch: 'Intel',
    fileName: 'unibot-studio-macos-x64',
    matches: (os, arch) => os === 'macos' && arch !== 'arm64',
  },
  {
    system: 'Windows',
    arch: 'x64',
    fileName: 'unibot-studio-windows-x64.exe',
    matches: (os) => os === 'windows',
  },
  {
    system: 'Linux',
    arch: 'x64',
    fileName: 'unibot-studio-linux-x64',
    matches: (os) => os === 'linux',
  },
]

const system = ref(null)

const matchedAsset = computed(() => {
  if (!system.value) return null
  return (
    platformOptions.find((option) => option.matches(system.value.os, system.value.arch)) || null
  )
})

const systemText = computed(() => {
  if (!system.value) return '检测中…'
  const name = OS_NAMES[system.value.os] || OS_NAMES.unknown
  return system.value.arch === 'arm64' ? `${name}（ARM）` : name
})

const downloadUrl = (fileName) => DOWNLOAD_BASE + fileName

async function detectSystem() {
  // 优先使用 Chromium 高熵 API，可准确区分 Apple Silicon / Intel
  try {
    const uaData = navigator.userAgentData
    if (uaData && typeof uaData.getHighEntropyValues === 'function') {
      const values = await uaData.getHighEntropyValues(['platform', 'architecture'])
      const platform = String(values.platform || '').toLowerCase()
      const architecture = String(values.architecture || '').toLowerCase()
      const os = platform.includes('mac')
        ? 'macos'
        : platform.includes('win')
          ? 'windows'
          : platform.includes('linux')
            ? 'linux'
            : 'unknown'
      const arch = architecture.includes('arm') ? 'arm64' : 'x64'
      if (os !== 'unknown') return { os, arch }
    }
  } catch {
    // 高熵 API 不可用时回退到 UA 判断
  }

  const ua = navigator.userAgent
  const os = /mac/i.test(ua)
    ? 'macos'
    : /win/i.test(ua)
      ? 'windows'
      : /linux/i.test(ua)
        ? 'linux'
        : 'unknown'
  const platform = String(navigator.platform || '').toLowerCase()
  const arch = /arm|aarch/i.test(ua) || /arm/i.test(platform) ? 'arm64' : 'x64'
  return { os, arch }
}

onMounted(async () => {
  system.value = await detectSystem()
})
</script>

<style scoped>
.aistudio-download {
  margin: 1rem 0;
}

.aistudio-download table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.aistudio-download th,
.aistudio-download td {
  padding: 0.5rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--vp-c-divider, #e2e2e3);
}

.aistudio-download th {
  font-weight: 600;
  color: var(--vp-c-text-2, #6b7280);
  background: var(--vp-c-bg-soft, #f6f6f7);
}

.aistudio-download tr.is-current {
  background: var(--vp-c-brand-soft, rgba(56, 132, 255, 0.15));
}

.aistudio-download td a {
  color: var(--vp-c-brand-1, #1a5fd0);
  text-decoration: none;
}

.aistudio-download td a:hover {
  text-decoration: underline;
}

.current-tag {
  margin-left: 0.5rem;
  font-size: 0.75rem;
  color: var(--vp-c-brand-1, #1a5fd0);
}

.detected-line {
  margin: 0.5rem 0 0;
  font-size: 0.875rem;
  color: var(--vp-c-text-2, #6b7280);
}
</style>
