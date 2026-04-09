<template>
  <div class="modal-overlay show" @click.self="$emit('close')">
    <div class="modal resource-modal">
      <h3>{{ editId ? '✏️ 编辑资源' : '📁 新建资源' }}</h3>
      <div class="form-group">
        <label>资源名称</label>
        <input type="text" v-model="name" placeholder="例：学习资料、电影合集" maxlength="50">
      </div>
      <div class="form-group" id="shareSelectorGroup">
        <label>关联分享链接 <small style="color:var(--gray-400);font-weight:normal;">(选择已有的分享进行关联)</small></label>
        <div class="selected-shares-preview">
          <span v-if="selectedShareIds.size === 0" style="color:var(--gray-400);font-size:12px;padding:4px 0;">暂未选择分享</span>
          <template v-else>
            <span style="font-size:11px;color:var(--gray-500);white-space:nowrap;flex-shrink:0;">已选 {{ selectedShareIds.size }} 个:</span>
            <span v-for="id in [...selectedShareIds]" :key="id" class="selected-share-chip">
              {{ getShareName(id) }}<span class="remove-chip" @click="selectedShareIds.delete(id)">×</span>
            </span>
          </template>
        </div>
        <div class="share-preview-filters">
          <select class="picker-platform-select" v-model="filterPlatform">
            <option value="">全部平台</option><option value="baidu">百度网盘</option><option value="quark">夸克网盘</option>
          </select>
          <label class="picker-expire-filter"><input type="checkbox" v-model="filterExpired"> 过滤已失效</label>
          <input type="text" class="share-search-box" v-model="filterKeyword" placeholder="🔍 搜索…">
        </div>
        <div class="share-preview-area">
          <div v-if="filteredShares.length === 0" style="padding:14px;text-align:center;color:var(--gray-400);font-size:12px;">无匹配的分享</div>
          <div v-for="s in filteredShares.slice(0, 3)" :key="s.id" class="share-selector-item" :class="{ selected: selectedShareIds.has(s.id) }" @click="toggleShare(s.id)">
            <input type="checkbox" :checked="selectedShareIds.has(s.id)" @click.stop="toggleShare(s.id)">
            <div class="share-selector-info">
              <div class="share-selector-name">{{ shorten(s.name, 30) }}</div>
              <div class="share-selector-meta">
                <span v-if="gp(s.source).sourceNameShort" class="selector-platform-tag" :class="gp(s.source).sourceClass">{{ gp(s.source).sourceNameShort }}</span>
                <span class="expire-badge" :class="getExpireClass(s.expire)">{{ s.expire || '未知' }}</span>
                <span v-if="s.pwd">🔒 有提取码</span>
              </div>
            </div>
          </div>
          <div v-if="filteredShares.length > 3" style="padding:6px 12px;text-align:center;color:var(--gray-400);font-size:11px;border-top:1px solid var(--gray-100);">还有 {{ filteredShares.length - 3 }} 条…</div>
        </div>
        <button v-if="availableShares.length > 3" class="btn btn-ghost share-expand-btn" @click="showPicker = true">📋 查看全部可选分享 ({{ filteredShares.length }})</button>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="save">保存</button>
      </div>
      <!-- 全量选择器弹窗 -->
      <div v-if="showPicker" class="modal-overlay show" style="position:absolute;" @click.self="showPicker = false">
        <div class="modal share-picker-modal">
          <h3 style="display:flex;align-items:center;justify-content:space-between;">
            <span>📋 选择分享链接</span>
            <button class="btn btn-ghost" @click="showPicker = false" style="padding:4px 10px;font-size:18px;line-height:1;">✕</button>
          </h3>
          <div class="share-picker-filters">
            <select class="picker-platform-select" v-model="filterPlatform"><option value="">全部平台</option><option value="baidu">百度网盘</option><option value="quark">夸克网盘</option></select>
            <label class="picker-expire-filter"><input type="checkbox" v-model="filterExpired"> 过滤已失效</label>
            <input type="text" class="share-search-box" v-model="filterKeyword" placeholder="🔍 搜索文件名、链接…">
          </div>
          <div class="share-picker-list">
            <div v-for="s in filteredShares" :key="s.id" class="share-selector-item" :class="{ selected: selectedShareIds.has(s.id) }" @click="toggleShare(s.id)">
              <input type="checkbox" :checked="selectedShareIds.has(s.id)" @click.stop="toggleShare(s.id)">
              <div class="share-selector-info">
                <div class="share-selector-name">{{ shorten(s.name, 30) }}</div>
                <div class="share-selector-meta">
                  <span v-if="gp(s.source).sourceNameShort" class="selector-platform-tag" :class="gp(s.source).sourceClass">{{ gp(s.source).sourceNameShort }}</span>
                  <span class="expire-badge" :class="getExpireClass(s.expire)">{{ s.expire || '未知' }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-actions">
            <div style="flex:1;font-size:12px;color:var(--gray-400);">已选 <strong style="color:var(--primary);">{{ selectedShareIds.size }}</strong> 条</div>
            <button class="btn btn-ghost" @click="showPicker = false">← 返回</button>
            <button class="btn btn-primary" @click="showPicker = false">确定选择</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { fetchAvailableShares, fetchResource, createResource, updateResource, updateResourceShares } from '../api.js'
import { getExpireClass, getPlatformInfo, toast } from '../utils.js'

const props = defineProps({ editId: Number })
const emit = defineEmits(['close', 'saved'])

const name = ref('')
const selectedShareIds = reactive(new Set())
const availableShares = ref([])
const showPicker = ref(false)
const filterPlatform = ref('')
const filterExpired = ref(true)
const filterKeyword = ref('')

function gp(s) { return getPlatformInfo(s) }
function shorten(s, n) { return s && s.length > n ? s.slice(0, n) + '…' : s || '' }

const filteredShares = computed(() => {
  let list = [...availableShares.value]
  if (filterPlatform.value) {
    const pf = filterPlatform.value
    list = list.filter(s => { const p = (s.source || '').includes(':') ? (s.source || '').split(':')[0] : s.source; return p === pf })
  }
  if (filterExpired.value) list = list.filter(s => s.expire !== '已失效')
  const kw = filterKeyword.value.toLowerCase()
  if (kw) list = list.filter(s => (s.name || '').toLowerCase().includes(kw) || (s.url || '').toLowerCase().includes(kw))
  return list
})

function toggleShare(id) {
  if (selectedShareIds.has(id)) selectedShareIds.delete(id); else selectedShareIds.add(id)
}

function getShareName(id) {
  const s = availableShares.value.find(s => s.id === id)
  const n = s ? s.name : `ID:${id}`
  return n.length > 15 ? n.slice(0, 15) + '…' : n
}

onMounted(async () => {
  const res = await fetchAvailableShares({ page_size: 200 })
  availableShares.value = res?.data || []
  if (props.editId) {
    const resource = await fetchResource(props.editId)
    if (resource) {
      name.value = resource.name || ''
      for (const s of (resource.shares || [])) selectedShareIds.add(s.id)
    }
  }
})

async function save() {
  if (!name.value.trim()) { toast('请输入资源名称', 'warning'); return }
  try {
    let resourceId
    if (props.editId) {
      await updateResource(props.editId, { name: name.value.trim() })
      resourceId = props.editId
      toast('资源更新成功', 'success')
    } else {
      const res = await createResource({ name: name.value.trim() })
      resourceId = res.id
      toast('资源创建成功', 'success')
    }
    await updateResourceShares(resourceId, [...selectedShareIds])
    emit('saved')
  } catch (e) { toast(e.message || '保存失败', 'error') }
}
</script>
