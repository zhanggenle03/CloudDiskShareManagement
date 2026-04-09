<template>
  <div v-if="shares.length === 0" class="empty-state">
    <div class="icon">🗂️</div><p>暂无分享记录</p><small>点击「导入」按钮上传CSV文件</small>
  </div>
  <div v-else class="cards-grid">
    <div v-for="item in shares" :key="item.id" class="card" :class="{ expired: item.expire === '已失效', selected: selected.has(item.id) }">
      <div class="card-header">
        <div class="card-header-top">
          <input type="checkbox" class="card-check" :checked="selected.has(item.id)" @change="$emit('toggle-select', item.id)">
          <span class="source-badge" :class="pi(item.source).sourceClass">{{ pi(item.source).sourceName }}</span>
          <span v-if="item.account_name" class="account-name-tag">{{ item.account_name }}</span>
        </div>
        <span class="card-name" :title="item.name">{{ item.name }}</span>
      </div>
      <div class="card-url">
        <a :href="item.url" target="_blank" :title="item.url">{{ item.url }}</a>
        <button class="copy-btn" @click="$emit('copy-link', item.url, $event.currentTarget)">复制</button>
      </div>
      <div class="card-meta">
        <span class="expire-badge" :class="getExpireClass(item.expire)">{{ item.expire || '未知' }}</span>
        <span v-if="item.pwd" class="pwd-tag" @click="$emit('copy-text', item.pwd, $event.currentTarget)">🔑 {{ item.pwd }}</span>
        <span class="meta-item">🕐 {{ item.share_time || '--' }}</span>
        <span v-if="item.view_count >= 0" class="meta-item">👁 {{ item.view_count }}</span>
      </div>
      <div v-if="item.tags" class="card-tags">
        <span v-for="t in parseTags(item.tags)" :key="t" class="tag" :class="getTagStyle(t, tagColors).cls" :style="getTagStyle(t, tagColors).style">
          {{ t }}<span class="del-tag" @click.stop="$emit('del-tag', item.id, t)">×</span>
        </span>
      </div>
      <div v-if="item.notes" class="card-notes">{{ item.notes }}</div>
      <div class="card-actions">
        <button class="action-btn" @click="$emit('edit', item.id)">✏️ 编辑</button>
        <button class="action-btn" @click="$emit('copy-share', item.name, item.url, item.pwd)">🔗 分享复制</button>
        <button class="action-btn danger" @click="$emit('delete', item.id)">🗑 删除</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { getExpireClass, getPlatformInfo, getTagStyle } from '../utils.js'
defineProps({ shares: Array, selected: Set, tagColors: Object })
defineEmits(['toggle-select', 'edit', 'delete', 'copy-link', 'copy-share', 'copy-text', 'del-tag'])
function pi(s) { return getPlatformInfo(s) }
function parseTags(tags) { return tags ? tags.split(',').filter(t => t.trim()) : [] }
</script>
