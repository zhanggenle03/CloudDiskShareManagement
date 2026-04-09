<template>
  <div class="modal-overlay show" @click.self="$emit('close')">
    <div class="modal" style="width:720px;height:680px;display:flex;flex-direction:column;">
      <h3>🔄 网盘同步</h3>
      <div class="sync-layout" style="display:flex;gap:12px;margin-top:12px;flex:1;min-height:0;">
        <!-- 左栏：平台选择 -->
        <div class="sync-platform-panel" style="width:180px;background:var(--gray-50);border-radius:8px;padding:10px;flex-shrink:0;">
          <div style="font-size:12px;font-weight:600;margin-bottom:8px;color:var(--gray-500);">选择平台</div>
          <div v-for="p in platforms" :key="p.key"
            class="sync-platform-item" :class="{ active: currentPlatform === p.key }"
            @click="selectPlatform(p.key)" :style="p.accounts.length === 0 ? 'opacity:0.5;' : ''">
            <div class="sync-platform-left">
              <input type="checkbox" class="sync-platform-checkbox"
                :checked="p.accounts.length > 0 && p.selected.size === p.accounts.length"
                :disabled="p.accounts.length === 0"
                @click.stop="togglePlatformAll(p.key)">
              <span class="sync-platform-name">{{ p.icon }} {{ p.name }}</span>
              <span class="sync-platform-count"><span :class="{ selected: p.accounts.length > 0 }">{{ p.selected.size }}</span>/{{ p.accounts.length }}</span>
            </div>
          </div>
        </div>
        <!-- 右栏：账号选择 -->
        <div class="sync-account-panel" style="flex:1;min-width:0;display:flex;flex-direction:column;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-shrink:0;">
            <div style="font-size:12px;font-weight:600;color:var(--gray-600);">{{ currentPlatformName }}</div>
            <div style="font-size:11px;color:var(--gray-500);">已选 <strong style="color:var(--primary);">{{ totalSelected }}</strong> 个</div>
          </div>
          <div style="flex:1;overflow-y:auto;border:1.5px solid var(--border);border-radius:8px;height:320px;">
            <div v-if="currentAccounts.length === 0" class="sync-account-empty">
              <div style="font-size:24px;margin-bottom:8px;">📭</div>
              <p>{{ currentPlatformName }}暂无账号</p>
              <p style="font-size:11px;margin-top:6px;color:var(--gray-500);">请先在账号管理中添加并配置Cookie</p>
            </div>
            <template v-else>
              <div v-if="validAccounts.length > 0" class="sync-account-group">
                <div class="sync-account-group-header">✅ 已验证 ({{ validAccounts.length }})</div>
                <div v-for="acc in validAccounts" :key="acc.id"
                  class="sync-account-item" :class="{ selected: platformData[currentPlatform]?.selected.has(acc.id) }"
                  @click="toggleAccount(currentPlatform, acc.id)">
                  <input type="checkbox" :checked="platformData[currentPlatform]?.selected.has(acc.id)"
                    @click.stop="toggleAccount(currentPlatform, acc.id)">
                  <div class="sync-account-info"><div class="sync-account-name">{{ acc.name }}</div></div>
                  <span class="sync-account-status valid">已验证</span>
                </div>
              </div>
              <div v-if="invalidAccounts.length > 0" class="sync-account-group">
                <div class="sync-account-group-header" style="color:var(--warning);">⚠️ 未验证/验证失败 ({{ invalidAccounts.length }})</div>
                <div v-for="acc in invalidAccounts" :key="acc.id"
                  class="sync-account-item" :class="{ selected: platformData[currentPlatform]?.selected.has(acc.id) }"
                  @click="toggleAccount(currentPlatform, acc.id)">
                  <input type="checkbox" :checked="platformData[currentPlatform]?.selected.has(acc.id)"
                    @click.stop="toggleAccount(currentPlatform, acc.id)">
                  <div class="sync-account-info"><div class="sync-account-name">{{ acc.name }}</div></div>
                  <span class="sync-account-status invalid">未验证</span>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
      <div style="padding:8px 12px;background:var(--gray-50);border-radius:6px;margin-top:8px;flex-shrink:0;font-size:11px;color:var(--gray-600);">
        <span v-if="totalSelected === 0">请先选择要同步的账号</span>
        <span v-else>已选择 <strong style="color:var(--primary);">{{ totalSelected }}</strong> 个账号进行同步</span>
      </div>
      <div class="modal-actions" style="margin-top:8px;flex-shrink:0;">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" :disabled="totalSelected === 0 || syncing" @click="doSync">{{ syncing ? '⏳ 同步中...' : '⚡ 开始同步' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { fetchAccounts, syncNow } from '../api.js'
import { toast } from '../utils.js'

const emit = defineEmits(['close', 'synced'])
const currentPlatform = ref('quark')
const syncing = ref(false)

const platformData = reactive({
  quark: { accounts: [], selected: new Set() },
  baidu: { accounts: [], selected: new Set() }
})

const platforms = computed(() => [
  { key: 'quark', name: '夸克网盘', icon: '🟣', accounts: platformData.quark.accounts, selected: platformData.quark.selected },
  { key: 'baidu', name: '百度网盘', icon: '🔵', accounts: platformData.baidu.accounts, selected: platformData.baidu.selected }
])

const currentPlatformName = computed(() => currentPlatform.value === 'quark' ? '🟣 夸克网盘账号' : '🔵 百度网盘账号')
const currentAccounts = computed(() => platformData[currentPlatform.value]?.accounts || [])
const validAccounts = computed(() => currentAccounts.value.filter(a => a.is_valid === 1))
const invalidAccounts = computed(() => currentAccounts.value.filter(a => a.is_valid !== 1))
const totalSelected = computed(() => platformData.quark.selected.size + platformData.baidu.selected.size)

onMounted(async () => {
  try {
    const [quarkRes, baiduRes] = await Promise.all([fetchAccounts('quark'), fetchAccounts('baidu')])
    const quarkAccounts = (quarkRes || []).filter(a => a.cookie && a.cookie.trim().length > 0)
    const baiduAccounts = (baiduRes || []).filter(a => a.cookie && a.cookie.trim().length > 0)
    platformData.quark.accounts = quarkAccounts
    platformData.quark.selected = new Set(quarkAccounts.filter(a => a.is_valid === 1).map(a => a.id))
    platformData.baidu.accounts = baiduAccounts
    platformData.baidu.selected = new Set(baiduAccounts.filter(a => a.is_valid === 1).map(a => a.id))
  } catch (e) { console.error('加载账号失败:', e) }
})

function selectPlatform(p) { currentPlatform.value = p }

function toggleAccount(platform, id) {
  const sel = platformData[platform].selected
  if (sel.has(id)) sel.delete(id); else sel.add(id)
}

function togglePlatformAll(platform) {
  const { accounts, selected } = platformData[platform]
  if (selected.size === accounts.length) selected.clear()
  else accounts.forEach(a => selected.add(a.id))
}

async function doSync() {
  const accountIds = []
  Object.keys(platformData).forEach(p => accountIds.push(...Array.from(platformData[p].selected)))
  if (accountIds.length === 0) return
  syncing.value = true
  let successCount = 0, failCount = 0, totalNew = 0, totalUpdated = 0
  try {
    for (const accountId of accountIds) {
      try {
        const res = await syncNow(accountId)
        if (res.success) { successCount++; totalNew += res.new_count || 0; totalUpdated += res.update_count || 0 }
        else failCount++
      } catch (e) { failCount++ }
    }
    if (failCount === 0) toast(`全部导入完成：新增 ${totalNew} 条，更新 ${totalUpdated} 条`, 'success')
    else if (successCount === 0) toast(`同步失败，${failCount} 个账号失败`, 'error')
    else toast(`部分同步完成：成功 ${successCount}/${accountIds.length}`, 'warning')
    emit('synced')
  } catch (e) { toast('同步请求失败', 'error') }
  finally { syncing.value = false }
}
</script>
