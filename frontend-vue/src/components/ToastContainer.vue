<template>
  <div class="toast-container">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
      <span>{{ icons[t.type] || 'ℹ️' }}</span><span>{{ t.msg }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { onToast } from '../utils.js'

const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' }
const toasts = ref([])
let idCounter = 0

const unsubscribe = onToast((msg, type) => {
  const id = ++idCounter
  toasts.value.push({ id, msg, type: type || 'info' })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, 3500)
})

onUnmounted(() => unsubscribe())
</script>
