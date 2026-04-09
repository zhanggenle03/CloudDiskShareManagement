<template>
  <aside class="sidebar">
    <div class="logo"><h1><span>☁️</span>云盘分享管理</h1></div>
    <div class="stats-mini">
      <div class="total">{{ stats.total || 0 }}</div>
      <div class="label">全部分享链接</div>
      <div class="stats-row">
        <div class="stat-chip"><div class="val">{{ stats.permanent || 0 }}</div><div class="lbl">永久</div></div>
        <div class="stat-chip"><div class="val">{{ stats.expiring || 0 }}</div><div class="lbl">限时</div></div>
        <div class="stat-chip"><div class="val">{{ stats.expired || 0 }}</div><div class="lbl">已失效</div></div>
      </div>
    </div>
    <div class="nav-section">
      <div class="nav-label">平台</div>
      <div class="nav-item" :class="{ active: source === 'all' }" @click="$emit('set-source', 'all')">
        <span class="icon">🗂</span> 全部 <span class="badge" :class="{ primary: source === 'all' }">{{ stats.total || 0 }}</span>
      </div>
      <div class="nav-item" :class="{ active: source === 'baidu' }" @click="$emit('set-source', 'baidu')">
        <span class="icon">🔵</span> 百度网盘 <span class="badge">{{ stats.baidu_count || 0 }}</span>
      </div>
      <div class="nav-item" :class="{ active: source === 'quark' }" @click="$emit('set-source', 'quark')">
        <span class="icon">🟣</span> 夸克网盘 <span class="badge">{{ stats.quark_count || 0 }}</span>
      </div>
    </div>
    <div class="nav-section">
      <div class="nav-label">操作</div>
      <div class="nav-dropdown" :class="{ open: importOpen }">
        <div class="nav-item nav-dropdown-trigger" @click="importOpen = !importOpen">
          <span class="icon">📥</span> 导入数据 <span class="dropdown-arrow" :style="{ transform: importOpen ? 'rotate(180deg)' : '' }">▾</span>
        </div>
        <div class="nav-dropdown-menu" v-show="importOpen">
          <div class="nav-dropdown-item" @click="$emit('show-import'); importOpen = false"><span class="icon">📄</span> CSV导入</div>
          <div class="nav-dropdown-item" @click="$emit('show-sync'); importOpen = false"><span class="icon">🔄</span> 网盘同步</div>
        </div>
      </div>
      <div class="nav-item" @click="$emit('show-logs')"><span class="icon">📋</span> 导入记录</div>
      <div class="nav-item" @click="$emit('show-accounts')"><span class="icon">👤</span> 账号管理</div>
    </div>
    <div class="nav-section" style="flex:1;overflow:hidden;display:flex;flex-direction:column;">
      <div class="nav-label">标签</div>
      <div class="tags-section">
        <template v-if="stats.tags && Object.keys(stats.tags).length > 0">
          <span v-for="([tagName, info]) in sortedTags" :key="tagName"
            class="tag-pill" :class="[info.color ? 'has-color' : 'no-color', { active: tag === tagName }]"
            :style="getTagPillStyle(tagName, info, tag === tagName)"
            @click="$emit('set-tag', tagName)" @contextmenu.prevent>
            <span v-if="info.color" class="dot" :style="{ background: info.color }"></span>
            {{ tagName }}<span style="opacity:.6">{{ info.count }}</span>
            <span class="del-pill" @click.stop="doDeleteTag(tagName)">×</span>
          </span>
        </template>
        <span v-else style="color:var(--gray-400);font-size:12px;padding:4px 10px;">暂无标签</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'
import { deleteTagEverywhere } from '../api.js'
import { toast } from '../utils.js'

const props = defineProps({ stats: Object, source: String, tag: String, tagColors: Object })
defineEmits(['set-source', 'set-tag', 'show-import', 'show-sync', 'show-logs', 'show-accounts'])
const importOpen = ref(false)

const sortedTags = computed(() => {
  if (!props.stats.tags) return []
  return Object.entries(props.stats.tags).sort((a, b) => b[1].count - a[1].count)
})

function getTagPillStyle(tagName, info, isActive) {
  const color = info.color
  if (!color) return isActive ? 'background:var(--primary);color:#fff;' : ''
  return isActive ? `background:${color};color:#fff;` : `background:${color}15;color:${color};`
}

async function doDeleteTag(tagName) {
  if (!confirm(`确认删除标签「${tagName}」？\n将从所有记录中移除该标签。`)) return
  await deleteTagEverywhere(tagName)
  toast(`已删除标签「${tagName}」`, 'success')
}
</script>
