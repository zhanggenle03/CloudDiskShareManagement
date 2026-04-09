/**
 * API 请求层
 */

const API = ''

export async function api(method, path, data) {
  const opts = { method, headers: {} }
  if (data instanceof FormData) {
    opts.body = data
  } else if (data) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(data)
  }
  const res = await fetch(API + path, opts)
  return res.json()
}

// ── 设置 ──
let _settingsCache = null

export async function loadSettings() {
  if (_settingsCache) return _settingsCache
  try {
    const res = await fetch(API + '/api/settings')
    _settingsCache = await res.json()
  } catch (e) {
    _settingsCache = {}
  }
  return _settingsCache || {}
}

export async function saveSetting(key, val) {
  const s = await loadSettings()
  s[key] = val
  _settingsCache = s
  try {
    await fetch(API + '/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: val })
    })
  } catch (e) {
    console.warn('saveSetting failed', e)
  }
}

export async function getSetting(key, defaultVal) {
  const s = await loadSettings()
  return s[key] !== undefined ? s[key] : defaultVal
}

// ── 分享 ──
export const fetchShares = (params) => api('GET', `/api/shares?${new URLSearchParams(params)}`)
export const fetchShare = (id) => api('GET', `/api/shares/${id}`)
export const updateShare = (id, data) => api('PUT', `/api/shares/${id}`, data)
export const deleteShare = (id, hard = false) => api('DELETE', `/api/shares/${id}${hard ? '?hard=true' : ''}`)
export const batchDeleteShares = (ids, hard = false) => api('POST', '/api/shares/batch_delete', { ids, hard })
export const batchTagShares = (ids, tag, action) => api('POST', '/api/shares/batch_tag', { ids, tag, action })

// ── 统计 ──
export const fetchStats = () => api('GET', '/api/stats')

// ── 标签颜色 ──
export const fetchTagColors = () => api('GET', '/api/tag_colors')
export const setTagColor = (name, color) => api('PUT', '/api/tag_colors', { name, color })
export const deleteTagColor = (name) => api('DELETE', `/api/tag_colors/${encodeURIComponent(name)}`)
export const deleteTagEverywhere = (name) => api('DELETE', `/api/tags/${encodeURIComponent(name)}`)

// ── 导入 ──
export const importCsv = (formData) => api('POST', '/api/import', formData)
export const fetchImportLogs = () => api('GET', '/api/import_logs')
export const clearImportLogs = () => api('DELETE', '/api/import_logs')

// ── 设置 API ──
export const fetchAllSettings = () => api('GET', '/api/settings')
export const updateSettings = (data) => api('PUT', '/api/settings', data)

// ── 账号 ──
export const fetchAccounts = (platform) => api('GET', `/api/accounts${platform ? '?platform=' + platform : ''}`)
export const fetchAccount = (id) => api('GET', `/api/accounts/${id}`)
export const createAccount = (data) => api('POST', '/api/accounts', data)
export const updateAccount = (id, data) => api('PUT', `/api/accounts/${id}`, data)
export const deleteAccount = (id) => api('DELETE', `/api/accounts/${id}`)
export const testAccountCookie = (id, data = {}) => api('POST', `/api/accounts/${id}/test`, data)

// ── 同步 ──
export const fetchSyncStatus = () => api('GET', '/api/sync/status')
export const syncNow = (accountId) => api('POST', '/api/sync/now', { account_id: accountId })

// ── 资源 ──
export const fetchResources = (params) => api('GET', `/api/resources?${new URLSearchParams(params)}`)
export const fetchResource = (id) => api('GET', `/api/resources/${id}`)
export const createResource = (data) => api('POST', '/api/resources', data)
export const updateResource = (id, data) => api('PUT', `/api/resources/${id}`, data)
export const deleteResource = (id) => api('DELETE', `/api/resources/${id}`)
export const updateResourceShares = (id, shareIds) => api('PUT', `/api/resources/${id}/shares`, { share_ids: shareIds })
export const removeShareFromResource = (resourceId, shareId) => api('DELETE', `/api/resources/${resourceId}/shares/${shareId}`)
export const fetchAvailableShares = (params) => api('GET', `/api/available_shares?${new URLSearchParams(params)}`)

// ── 进程管理 ──
export const shutdownService = () => fetch('/api/shutdown', { method: 'POST', keepalive: true }).catch(() => {})
export const restartService = () => fetch('/api/restart', { method: 'POST' })
