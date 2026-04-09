<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <input type="checkbox" class="select-all-check" @change="$emit('select-all', $event.target.checked)">
      <span class="result-info">共 {{ total }} 条{{ keyword ? `（关键词：${keyword}）` : '' }}</span>
      <button v-if="viewMode === 'folder'" class="btn btn-primary" @click="$emit('add-resource')" style="padding:6px 14px;font-size:13px;">+ 新建资源</button>
      <div v-if="selectedCount > 0 && viewMode !== 'folder'" style="display:flex;gap:10px;align-items:center;margin-left:12px;">
        <button class="btn btn-primary" @click="$emit('batch-tag')" style="padding:6px 14px;font-size:13px;">🏷️ 批量添加标签</button>
        <button class="btn btn-danger" @click="$emit('batch-delete')" style="padding:6px 14px;font-size:13px;">🗑 删除 ({{ selectedCount }})</button>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;">
      <div class="view-tabs">
        <button class="view-tab-btn" :class="{ active: viewMode === 'card' }" @click="$emit('set-view', 'card')">▦ 卡片</button>
        <button class="view-tab-btn" :class="{ active: viewMode === 'list' }" @click="$emit('set-view', 'list')">☰ 列表</button>
        <button class="view-tab-btn" :class="{ active: viewMode === 'folder' }" @click="$emit('set-view', 'folder')">📁 文件夹</button>
      </div>
      <select class="pagesize-select" :value="pageSize" @change="$emit('set-page-size', $event.target.value)">
        <option value="10">10 条/页</option><option value="20">20 条/页</option>
        <option value="50">50 条/页</option><option value="100">100 条/页</option>
      </select>
      <select class="sort-select" :value="sortValue" @change="$emit('set-sort', $event.target.value)">
        <template v-if="viewMode === 'folder'">
          <option value="updated_at_desc">更新时间↓</option><option value="updated_at_asc">更新时间↑</option>
          <option value="name_asc">名称A-Z</option><option value="name_desc">名称Z-A</option>
        </template>
        <template v-else>
          <option value="share_time_desc">分享时间↓</option><option value="share_time_asc">分享时间↑</option>
          <option value="name_asc">名称A-Z</option><option value="name_desc">名称Z-A</option>
        </template>
      </select>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  viewMode: String, pageSize: Number, sort: String, order: String, selectedCount: Number, total: Number, keyword: String
})
defineEmits(['set-view', 'set-page-size', 'set-sort', 'select-all', 'batch-tag', 'batch-delete', 'add-resource'])
const sortValue = computed(() => `${props.sort}_${props.order}`)
</script>
