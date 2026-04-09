<template>
  <div class="layout" :data-theme="store.theme">
    <Sidebar
      :stats="store.stats"
      :source="store.source"
      :tag="store.tag"
      :tagColors="store.tagColors"
      @set-source="setSource"
      @set-tag="setTagFilter"
      @show-import="showImportModal = true"
      @show-sync="showSyncModal = true"
      @show-logs="showLogModal = true"
      @show-accounts="showAccountModal = true"
    />

    <main class="main">
      <TopBar
        :theme="store.theme"
        :expire="store.expire"
        :keyword="store.keyword"
        @toggle-theme="toggleTheme"
        @set-expire="setExpire"
        @search="debounceSearch"
        @show-about="showAboutModal = true"
        @restart="handleRestart"
        @exit="handleExit"
      />

      <div class="content">
        <Toolbar
          :viewMode="store.viewMode"
          :pageSize="store.pageSize"
          :sort="store.sort"
          :order="store.order"
          :selectedCount="store.selected.size"
          :total="store.total"
          :keyword="store.keyword"
          @set-view="setView"
          @set-page-size="setPageSize"
          @set-sort="setSort"
          @select-all="toggleSelectAll"
          @batch-tag="showBatchTagModal = true"
          @batch-delete="batchDeleteSelected"
          @add-resource="openAddResourceModal"
        />

        <!-- 卡片视图 -->
        <CardsView
          v-if="store.viewMode === 'card'"
          :shares="shares"
          :selected="store.selected"
          :tagColors="store.tagColors"
          @toggle-select="toggleSelect"
          @edit="openEditModal"
          @delete="softDelete"
          @copy-link="copyLinkOnly"
          @copy-share="copyShare"
          @copy-text="copyText"
          @del-tag="delTagFromCard"
        />

        <!-- 列表视图 -->
        <ListView
          v-if="store.viewMode === 'list'"
          :shares="shares"
          :selected="store.selected"
          :tagColors="store.tagColors"
          @toggle-select="toggleSelect"
          @edit="openEditModal"
          @delete="softDelete"
          @copy-link="copyLinkOnly"
          @copy-share="copyShare"
          @copy-text="copyText"
          @del-tag="delTagFromCard"
        />

        <!-- 文件夹视图 -->
        <FolderView
          v-if="store.viewMode === 'folder'"
          :resources="store.resourceState.resources"
          :expandedId="store.resourceState.expandedId"
          :selectedResourceIds="store.resourceState.selectedResourceIds"
          @toggle-expand="toggleResourceExpand"
          @toggle-select-resource="toggleResourceSelect"
          @edit-resource="openEditResourceModal"
          @delete-resource="handleDeleteResource"
          @remove-share="handleRemoveShareFromResource"
          @copy-text="copyText"
        />

        <!-- 分页 -->
        <Pagination
          v-if="store.viewMode !== 'folder'"
          :total="store.total"
          :page="store.page"
          :pageSize="store.pageSize"
          @go-page="goPage"
        />
      </div>
    </main>

    <!-- 弹窗们 -->
    <EditModal v-if="showEditModal" :shareId="editingShareId" @close="showEditModal = false" @saved="onShareSaved" />
    <ImportModal v-if="showImportModal" @close="showImportModal = false" @imported="onImported" />
    <SyncModal v-if="showSyncModal" @close="showSyncModal = false" @synced="onSynced" />
    <LogModal v-if="showLogModal" @close="showLogModal = false" />
    <AccountModal v-if="showAccountModal" @close="showAccountModal = false" />
    <BatchTagModal v-if="showBatchTagModal" :selectedIds="[...store.selected]" @close="showBatchTagModal = false" @done="onBatchTagDone" />
    <AboutModal v-if="showAboutModal" @close="showAboutModal = false" />
    <ResourceModal v-if="showResourceModal" :editId="resourceEditId" @close="showResourceModal = false" @saved="onResourceSaved" />

    <!-- Toast -->
    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { store, toggleSelect, clearSelection } from './store.js'
import {
  fetchStats, fetchShares, deleteShare, batchDeleteShares, batchTagShares,
  deleteTagEverywhere, syncNow, saveSetting, loadSettings, getSetting,
  fetchResources, fetchResource, removeShareFromResource as apiRemoveShareFromResource,
  shutdownService, restartService
} from './api.js'
import { toast, copyToClipboard, escHtml } from './utils.js'

import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'
import Toolbar from './components/Toolbar.vue'
import CardsView from './components/CardsView.vue'
import ListView from './components/ListView.vue'
import FolderView from './components/FolderView.vue'
import Pagination from './components/Pagination.vue'
import EditModal from './components/EditModal.vue'
import ImportModal from './components/ImportModal.vue'
import SyncModal from './components/SyncModal.vue'
import LogModal from './components/LogModal.vue'
import AccountModal from './components/AccountModal.vue'
import BatchTagModal from './components/BatchTagModal.vue'
import AboutModal from './components/AboutModal.vue'
import ResourceModal from './components/ResourceModal.vue'
import ToastContainer from './components/ToastContainer.vue'

// ── 分享数据 ──
const shares = ref([])

// ── 弹窗状态 ──
const showEditModal = ref(false)
const showImportModal = ref(false)
const showSyncModal = ref(false)
const showLogModal = ref(false)
const showAccountModal = ref(false)
const showBatchTagModal = ref(false)
const showAboutModal = ref(false)
const showResourceModal = ref(false)
const editingShareId = ref(null)
const resourceEditId = ref(null)

// ── 搜索防抖 ──
let searchTimer = null

function debounceSearch(keyword) {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.keyword = keyword
    store.page = 1
    if (store.viewMode === 'folder') {
      loadResourceView()
    } else {
      loadShares()
    }
  }, 350)
}

// ── 加载分享列表 ──
async function loadShares() {
  const params = {
    source: store.source,
    expire: store.expire,
    keyword: store.keyword,
    tag: store.tag,
    page: store.page,
    page_size: store.pageSize,
    sort: store.sort,
    order: store.order
  }
  const data = await fetchShares(params)
  shares.value = data.data || []
  store.total = data.total || 0
  store.selected.clear()
}

// ── 加载统计 ──
async function loadStats() {
  const s = await fetchStats()
  store.stats = s
  // 更新标签颜色
  if (s.tags) {
    const colorMap = {}
    for (const [tag, info] of Object.entries(s.tags)) {
      colorMap[tag] = info.color || ''
    }
    store.tagColors = colorMap
  }
}

// ── 加载资源视图 ──
async function loadResourceView() {
  const params = {
    sort: store.sort || 'updated_at',
    order: store.order || 'desc',
    page: store.page || 1,
    page_size: store.pageSize || 50,
    keyword: store.keyword || ''
  }
  const res = await fetchResources(params)
  store.resourceState.resources = res.data || []
}

// ── 筛选控制 ──
function setSource(src) {
  store.source = src
  store.page = 1
  loadShares()
}

function setExpire(expire) {
  store.expire = expire
  store.page = 1
  loadShares()
}

function setTagFilter(tag) {
  store.tag = store.tag === tag ? '' : tag
  store.page = 1
  loadShares()
}

async function setView(mode) {
  store.viewMode = mode
  await saveSetting('viewMode', mode)

  if (mode === 'folder') {
    store.source = 'all'
    store.expire = ''
    store.resourceState.selectedResourceIds.clear()
    await loadResourceView()
  } else {
    await loadShares()
  }
}

async function setPageSize(val) {
  store.pageSize = parseInt(val)
  store.page = 1
  await saveSetting('pageSize', String(val))
  if (store.viewMode === 'folder') {
    loadResourceView()
  } else {
    loadShares()
  }
}

async function setSort(val) {
  const isAsc = val.endsWith('_asc')
  const isDesc = val.endsWith('_desc')
  if (isAsc || isDesc) {
    const parts = val.split('_')
    if (parts.length > 2) {
      const sortField = parts.slice(0, -1).join('_')
      store.sort = sortField
    } else {
      store.sort = parts[0]
    }
    store.order = isAsc ? 'asc' : 'desc'
  }
  store.page = 1
  await saveSetting('sort', val)
  if (store.viewMode === 'folder') {
    loadResourceView()
  } else {
    loadShares()
  }
}

function goPage(p) {
  const totalPages = Math.ceil(store.total / store.pageSize)
  if (p < 1 || p > totalPages) return
  store.page = p
  loadShares()
}

// ── 选择 ──
function toggleSelectAll(checked) {
  if (checked) {
    store.selected.clear()
    shares.value.forEach(s => store.selected.add(s.id))
  } else {
    store.selected.clear()
  }
}

// ── 删除 ──
async function softDelete(id) {
  if (!confirm('确认删除这条分享记录？')) return
  await deleteShare(id)
  toast('已删除', 'success')
  loadShares()
  loadStats()
}

async function batchDeleteSelected() {
  if (store.selected.size === 0) return
  if (!confirm(`确认删除选中的 ${store.selected.size} 条记录？`)) return
  await batchDeleteShares([...store.selected])
  toast(`已删除 ${store.selected.size} 条`, 'success')
  store.selected.clear()
  loadShares()
  loadStats()
}

// ── 标签 ──
async function delTagFromCard(shareId, tag) {
  await batchTagShares([shareId], tag, 'remove')
  loadShares()
  loadStats()
}

// ── 编辑弹窗 ──
function openEditModal(id) {
  editingShareId.value = id
  showEditModal.value = true
}

function onShareSaved() {
  showEditModal.value = false
  loadShares()
  loadStats()
}

// ── 导入完成 ──
function onImported() {
  showImportModal.value = false
  store.page = 1
  loadStats()
  loadShares()
}

// ── 同步完成 ──
function onSynced() {
  loadStats()
  loadShares()
}

// ── 批量标签完成 ──
function onBatchTagDone() {
  showBatchTagModal.value = false
  store.selected.clear()
  loadShares()
  loadStats()
}

// ── 复制 ──
function copyText(text, btn) {
  if (!btn) return
  const origText = btn.textContent
  copyToClipboard(text).then(() => {
    btn.textContent = '已复制'
    btn.classList.add('copied')
    setTimeout(() => {
      if (btn && btn.classList.contains('copied')) {
        btn.textContent = origText
        btn.classList.remove('copied')
      }
    }, 2000)
    toast('已复制到剪贴板', 'success')
  })
}

function copyLinkOnly(url, btn) {
  copyText(url, btn)
}

function copyShare(name, url, pwd) {
  let text = `${name}\n${url}`
  if (pwd) text += `\n提取码：${pwd}`
  copyToClipboard(text).then(() => toast('已复制到剪贴板', 'success'))
}

// ── 主题 ──
async function toggleTheme() {
  const next = store.theme === 'dark' ? 'light' : 'dark'
  store.theme = next
  document.documentElement.setAttribute('data-theme', next)
  await saveSetting('theme', next)
}

// ── 退出/重启 ──
function handleExit() {
  if (!confirm('确定要退出程序吗？')) return
  shutdownService()
  document.body.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:center;height:100vh;
                background:var(--bg);color:var(--text-secondary);font-size:15px;flex-direction:column;gap:12px;">
      <div style="font-size:28px;">👋</div>
      <div>程序已安全退出</div>
      <div style="font-size:12px;color:var(--gray-400);">你可以关闭此页面</div>
    </div>`
}

function handleRestart() {
  if (!confirm('确定要重启服务吗？')) return
  document.body.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:center;height:100vh;
                background:var(--bg);color:var(--text-secondary);font-size:15px;flex-direction:column;gap:16px;">
      <div style="font-size:40px;animation:pulse 1.5s ease-in-out infinite;">🔄</div>
      <div id="restartTitle" style="font-size:16px;">正在重启服务...</div>
      <div style="width:200px;height:4px;background:var(--border);border-radius:2px;overflow:hidden;">
        <div id="restartBar" style="height:100%;background:var(--primary);width:0%;transition:width 0.3s;"></div>
      </div>
      <div id="restartHint" style="font-size:12px;color:var(--gray-400);">正在终止旧进程</div>
    </div>
    <style>@keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.1);opacity:.8}}</style>`

  restartService().then(() => {
    let attempts = 0
    function tryPoll() {
      attempts++
      fetch('/api/stats').then(res => {
        if (res.ok) {
          location.reload()
        } else {
          setTimeout(tryPoll, attempts < 10 ? 1000 : 2000)
        }
      }).catch(() => {
        if (attempts >= 60) return
        setTimeout(tryPoll, attempts < 10 ? 1000 : 2000)
      })
    }
    setTimeout(tryPoll, 3000)
  })
}

// ── 资源（文件夹视图） ──
function toggleResourceExpand(resourceId) {
  if (store.resourceState.expandedId === resourceId) {
    store.resourceState.expandedId = null
  } else {
    // 获取详情
    fetchResource(resourceId).then(res => {
      if (res) {
        const idx = store.resourceState.resources.findIndex(r => r.id === resourceId)
        if (idx >= 0) store.resourceState.resources[idx] = res
      }
    })
    store.resourceState.expandedId = resourceId
  }
}

function toggleResourceSelect(id) {
  if (store.resourceState.selectedResourceIds.has(id)) {
    store.resourceState.selectedResourceIds.delete(id)
  } else {
    store.resourceState.selectedResourceIds.add(id)
  }
}

function openAddResourceModal() {
  resourceEditId.value = null
  showResourceModal.value = true
}

function openEditResourceModal(id) {
  resourceEditId.value = id
  showResourceModal.value = true
}

async function handleDeleteResource(id) {
  const r = store.resourceState.resources.find(r => r.id === id)
  const name = r ? r.name : ''
  if (!confirm(`确认删除资源「${name}」？\n仅删除分组关系，不会删除关联的原始分享记录。`)) return
  const { deleteResource } = await import('./api.js')
  await deleteResource(id)
  toast('资源已删除', 'success')
  if (store.resourceState.expandedId === id) store.resourceState.expandedId = null
  loadResourceView()
}

async function handleRemoveShareFromResource(resourceId, shareId) {
  await apiRemoveShareFromResource(resourceId, shareId)
  toast('已移除关联', 'success')
  const res = await fetchResource(resourceId)
  const idx = store.resourceState.resources.findIndex(r => r.id === resourceId)
  if (idx >= 0 && res) store.resourceState.resources[idx] = res
}

function onResourceSaved() {
  showResourceModal.value = false
  loadResourceView()
}

// ── 页面关闭/刷新 ──
const CLOSE_KEY = 'closing'
let closeTimer = null

function sendShutdown() {
  try {
    const data = new Blob([JSON.stringify({})], { type: 'application/json' })
    navigator.sendBeacon('/api/shutdown', data)
  } catch (e) {
    try {
      fetch('/api/shutdown', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}), keepalive: true }).catch(() => {})
    } catch (e2) {}
  }
}

function onLoad() {
  if (sessionStorage.getItem(CLOSE_KEY) === '1') {
    sessionStorage.removeItem(CLOSE_KEY)
    if (closeTimer) { clearTimeout(closeTimer); closeTimer = null }
  }
}

function onBeforeUnload() {
  sessionStorage.setItem(CLOSE_KEY, '1')
  closeTimer = setTimeout(() => sendShutdown(), 500)
}

// ── 初始化 ──
async function init() {
  try {
    const s = await loadSettings()
    store.theme = s.theme || 'light'
    document.documentElement.setAttribute('data-theme', store.theme)
    store.viewMode = s.viewMode || 'card'
    store.pageSize = parseInt(s.pageSize) || 20
    const savedSort = s.sort || 'share_time_desc'
    const parts = savedSort.split('_')
    store.sort = parts[0] === 'name' ? 'name' : (parts[0] === 'updated_at' ? 'updated_at' : 'share_time')
    store.order = parts[1] || 'desc'
  } catch (e) {
    console.error('加载设置失败', e)
  }

  try {
    await loadStats()
    if (store.viewMode === 'folder') {
      await loadResourceView()
    } else {
      await loadShares()
    }
  } catch (e) {
    console.error('加载数据失败', e)
  }
}

onMounted(() => {
  init()
  window.addEventListener('load', onLoad)
  window.addEventListener('beforeunload', onBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('load', onLoad)
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>
