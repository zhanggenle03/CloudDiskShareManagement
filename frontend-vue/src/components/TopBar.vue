<template>
  <div class="topbar">
    <div class="topbar-left">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" :value="keyword" placeholder="搜索文件名、链接、备注…" @input="$emit('search', $event.target.value)">
      </div>
      <div class="filter-group">
        <button class="filter-btn" :class="{ active: expire === '' }" @click="$emit('set-expire', '')">全部</button>
        <button class="filter-btn" :class="{ active: expire === 'permanent' }" @click="$emit('set-expire', 'permanent')">永久</button>
        <button class="filter-btn" :class="{ active: expire === 'limited' }" @click="$emit('set-expire', 'limited')">限时</button>
        <button class="filter-btn" :class="{ active: expire === 'expired' }" @click="$emit('set-expire', 'expired')">已失效</button>
      </div>
    </div>
    <button class="theme-toggle" @click="$emit('toggle-theme')" title="切换主题">
      <span>{{ theme === 'dark' ? '☀️' : '🌙' }}</span>
    </button>
    <button class="theme-toggle" @click="$emit('show-about')" title="关于" style="margin-right:8px;">⚙️</button>
    <button class="theme-toggle exit-btn" @click="$emit('exit')" title="退出">⏻</button>
  </div>
</template>

<script setup>
defineProps({ theme: String, expire: String, keyword: String })
defineEmits(['toggle-theme', 'set-expire', 'search', 'show-about', 'restart', 'exit'])
</script>
