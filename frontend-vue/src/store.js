/**
 * 全局响应式状态（简易 store，使用 Vue 3 reactive）
 */
import { reactive, computed } from 'vue'

export const store = reactive({
  // 分享列表状态
  source: 'all',
  expire: '',
  keyword: '',
  tag: '',
  sort: 'share_time',
  order: 'desc',
  page: 1,
  pageSize: 20,
  total: 0,
  selected: new Set(),
  viewMode: 'card',
  tagColors: {},
  theme: 'light',

  // 统计
  stats: {
    total: 0,
    baidu_count: 0,
    quark_count: 0,
    permanent: 0,
    expiring: 0,
    expired: 0,
    tags: {}
  },

  // 同步状态
  syncState: {
    accounts: [],
    platforms: {
      quark: { accounts: [], selected: new Set() },
      baidu: { accounts: [], selected: new Set() }
    },
    currentPlatform: null
  },

  // 账号管理状态
  accountState: {
    currentPlatform: 'quark',
    accounts: []
  },

  // 资源（文件夹视图）状态
  resourceState: {
    resources: [],
    expandedId: null,
    selectedShareIds: new Set(),
    selectedResourceIds: new Set(),
    availableShares: [],
    filteredShares: [],
    shareSearchKeyword: '',
    previewPlatform: '',
    previewHideExpired: true,
    previewSearchKeyword: '',
    pickerPlatform: '',
    pickerHideExpired: false
  }
})

export const selectedCount = computed(() => store.selected.size)

export function toggleSelect(id) {
  if (store.selected.has(id)) {
    store.selected.delete(id)
  } else {
    store.selected.add(id)
  }
}

export function clearSelection() {
  store.selected.clear()
}
