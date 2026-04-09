<template>
  <div v-if="resources.length === 0" class="resource-empty-state">
    <div class="icon">📂</div><p>暂无资源文件夹</p><small>点击右上角「新建资源」创建第一个资源</small>
  </div>
  <div v-else class="resource-list">
    <div v-for="r in resources" :key="r.id" class="resource-item" :class="{ expanded: expandedId === r.id }">
      <div class="resource-header">
        <input type="checkbox" class="resource-check" :checked="selectedResourceIds.has(r.id)" @click.stop="$emit('toggle-select-resource', r.id)">
        <div class="resource-icon" @click="$emit('toggle-expand', r.id)">📁</div>
        <div class="resource-info" @click="$emit('toggle-expand', r.id)">
          <div class="resource-name-row">
            <span class="resource-name">{{ r.name }}</span>
            <div class="resource-platform-tags">
              <span v-for="p in getPlatforms(r)" :key="p" class="res-platform-tag" :class="p">{{ p === 'baidu' ? '百度网盘' : '夸克网盘' }}</span>
            </div>
          </div>
          <div class="resource-meta">
            <span>{{ (r.shares || []).length }} 个关联链接</span>
            <span>更新于 {{ formatTime(r.updated_at) }}</span>
          </div>
        </div>
        <div class="resource-actions-btns">
          <button class="res-act-btn" @click="$emit('edit-resource', r.id)">✏️ 编辑</button>
          <button class="res-act-btn danger" @click="$emit('delete-resource', r.id)">🗑 删除</button>
        </div>
        <span class="resource-arrow">▶</span>
      </div>
      <div class="resource-drawer"><div class="drawer-inner">
        <template v-if="(r.shares || []).length === 0">
          <div class="drawer-empty"><div style="font-size:24px;margin-bottom:6px;">🔗</div>暂无关联的分享链接</div>
        </template>
        <template v-else>
          <div class="drawer-share-list">
            <div v-for="s in r.shares" :key="s.id" class="drawer-share-item">
              <span class="drawer-share-source"><span class="source-badge" :class="gp(s.source).sourceClass" style="font-size:10px;padding:1px 6px;">{{ gp(s.source).sourceNameShort }}</span></span>
              <span class="drawer-share-name">{{ s.name }}</span>
              <a class="drawer-share-url" :href="s.url" target="_blank">{{ s.url }}</a>
              <span v-if="s.pwd" class="drawer-share-pwd" @click="$emit('copy-text', s.pwd, $event.currentTarget)">🔑{{ s.pwd }}</span>
              <button class="drawer-share-copy" @click="$emit('copy-text', s.url, $event.currentTarget)">📋</button>
              <button class="drawer-share-remove" @click.stop="$emit('remove-share', r.id, s.id)">✕</button>
            </div>
          </div>
        </template>
      </div></div>
    </div>
  </div>
</template>

<script setup>
import { getPlatformInfo, formatTime } from '../utils.js'
defineProps({ resources: Array, expandedId: Number, selectedResourceIds: Set })
defineEmits(['toggle-expand', 'toggle-select-resource', 'edit-resource', 'delete-resource', 'remove-share', 'copy-text'])
function gp(s) { return getPlatformInfo(s) }
function getPlatforms(resource) {
  const ps = new Set()
  for (const s of (resource.shares || [])) { let p = s.source || ''; if (p.includes(':')) p = p.split(':')[0]; if (p) ps.add(p) }
  return [...ps]
}
</script>
