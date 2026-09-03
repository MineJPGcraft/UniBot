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
    <p class="detected-line">最新版本：{{ releaseText }}（来自 GitHub Releases）</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

// 与 UniBot 内置 Studio 管理器（Scripts/Managers/Studio.py）保持一致的资产命名，
// 下载地址改为从 GitHub Releases（Minecraft-UniBot/AiStudio）的最新 Release 抓取
const RELEASE_API_URL = 'https://api.github.com/repos/Minecraft-UniBot/AiStudio/releases/latest'
const RELEASES_PAGE_URL = 'https://github.com/Minecraft-UniBot/AiStudio/releases/'

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

// GitHub 最新 Release 信息：{ tagName, assets: { [fileName]: browser_download_url } }
const release = ref(null)

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

const releaseText = computed(() => {
  if (!release.value) return '获取中…'
  return release.value.tagName || '未知'
})

const downloadUrl = (fileName) => {
  const assetUrl = release.value?.assets?.[fileName]
  // Release 未加载或缺少对应资产时，回退到 Releases 页面
  return assetUrl || RELEASES_PAGE_URL
}

async function fetchLatestRelease() {
  const response = await fetch(RELEASE_API_URL, {
    headers: { Accept: 'application/vnd.github+json' },
  })
  if (!response.ok) throw new Error(`GitHub API 响应异常：${response.status}`)
  const data = await response.json()
  if (data.draft) throw new Error('最新 Release 为草稿，暂不可下载')
  const assets = {}
  for (const asset of data.assets || []) {
    if (asset.name && asset.browser_download_url) assets[asset.name] = asset.browser_download_url
  }
  release.value = { tagName: data.tag_name || '', assets }
}

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
  try {
    await fetchLatestRelease()
  } catch (error) {
    // 抓取失败（网络受限 / API 限流等）时保持回退链接，并提示用户前往 Releases 页面
    console.warn('[AiStudioDownload] 获取 GitHub 最新 Release 失败：', error)
    release.value = { tagName: '', assets: {} }
  }
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
