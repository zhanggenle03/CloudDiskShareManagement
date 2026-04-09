<template>
  <div v-if="shares.length === 0" class="empty-state">
    <div class="icon">🗂️</div><p>暂无分享记录</p>
  </div>
  <div v-else class="table-view">
    <table>
      <thead><tr>
        <th></th><th>文件名</th><th class="th-center">平台</th><th class="th-center">账号</th>
        <th>链接</th><th class="th-center">提取码</th><th class="th-center">有效期</th>
        <th class="th-center">分享时间</th><th class="th-center">标签</th><th class="th-center">备注</th><th class="th-center">操作</th>
      </tr></thead>
      <tbody>
        <tr v-for="item in shares" :key="item.id" :class="{ expired: item.expire === '已失效', selected: selected.has(item.id) }">
          <td class="td-check"><input type="checkbox" class="card-check" :checked="selected.has(item.id)" @change="$emit('toggle-select', item.id)"></td>
          <td class="td-name" :title="item.name">{{ shorten(item.name, 25) }}</td>
          <td class="td-source"><span class="source-badge" :class="pi(item.source).sourceClass">{{ pi(item.source).sourceNameShort }}</span></td>
          <td>{{ item.account_name || '—' }}</td>
          <td class="td-url"><a :href="item.url" target="_blank">{{ item.url }}</a><button class="copy-btn" style="margin-left:4px" @click="$emit('copy-link', item.url, $event.currentTarget)">复制</button></td>
          <td class="td-pwd"><span v-if="item.pwd" class="pwd-tag" @click="$emit('copy-text', item.pwd, $event.currentTarget)">🔑{{ item.pwd }}</span><span v-else style="color:var(--gray-400)">—</span></td>
          <td class="td-meta"><span class="expire-badge" :class="getExpireClass(item.expire)">{{ item.expire || '未知' }}</span></td>
          <td class="td-meta">{{ item.share_time || '--' }}</td>
          <td class="td-tags">
            <template v-if="item.tags"><span v-for="t in parseTags(item.tags)" :key="t" class="tag" :class="getTagStyle(t, tagColors).cls" :style="getTagStyle(t, tagColors).style">{{ t }}<span class="del-tag" @click.stop="$emit('del-tag', item.id, t)">×</span></span></template>
            <span v-else style="color:var(--gray-400)">—</span>
          </td>
          <td class="td-notes">{{ item.notes ? '📝' : '—' }}</td>
          <td class="td-actions">
            <button class="action-btn" @click="$emit('edit', item.id)">✏️</button>
            <button class="action-btn danger" @click="$emit('delete', item.id)">🗑</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { getExpireClass, getPlatformInfo, getTagStyle } from '../utils.js'
defineProps({ shares: Array, selected: Set, tagColors: Object })
defineEmits(['toggle-select', 'edit', 'delete', 'copy-link', 'copy-share', 'copy-text', 'del-tag'])
function pi(s) { return getPlatformInfo(s) }
function parseTags(tags) { return tags ? tags.split(',').filter(t => t.trim()) : [] }
function shorten(s, n) { return s && s.length > n ? s.slice(0, n) + '…' : s || '' }
</script>
