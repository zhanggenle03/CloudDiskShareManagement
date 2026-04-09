<template>
  <div class="pagination" v-if="totalPages > 1">
    <button class="page-btn" :disabled="page <= 1" @click="$emit('go-page', page - 1)">‹</button>
    <template v-for="i in totalPages" :key="i">
      <button v-if="i === 1 || i === totalPages || Math.abs(i - page) <= 2"
        class="page-btn" :class="{ active: i === page }" @click="$emit('go-page', i)">{{ i }}</button>
      <span v-else-if="Math.abs(i - page) === 3" style="padding:0 4px;color:var(--gray-400)">…</span>
    </template>
    <button class="page-btn" :disabled="page >= totalPages" @click="$emit('go-page', page + 1)">›</button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ total: Number, page: Number, pageSize: Number })
defineEmits(['go-page'])
const totalPages = computed(() => Math.ceil(props.total / props.pageSize))
</script>
