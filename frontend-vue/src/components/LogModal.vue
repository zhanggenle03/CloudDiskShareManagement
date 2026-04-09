<template>
  <div class="modal-overlay show" @click.self="$emit('close')">
    <div class="modal" style="width:640px">
      <h3>📋 导入记录</h3>
      <div style="max-height:360px;overflow-y:auto;margin-top:8px;">
        <p v-if="logs.length === 0" style="color:var(--gray-400);padding:20px;text-align:center;">暂无导入记录</p>
        <table v-else class="log-table">
          <thead><tr><th>数据来源</th><th>平台</th><th>总数</th><th>新增</th><th>更新</th><th>时间</th></tr></thead>
          <tbody>
            <tr v-for="l in logs" :key="l.id">
              <td>{{ l.filename }}</td>
              <td><span class="source-badge" :class="getSourceInfo(l.source).sourceClass">{{ getSourceInfo(l.source).sourceNameShort }}</span></td>
              <td>{{ l.total }}</td>
              <td style="color:var(--success)">{{ l.imported }}</td>
              <td style="color:var(--warning)">{{ l.skipped }}</td>
              <td>{{ l.import_time }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="modal-actions">
        <button class="btn btn-danger" @click="clearLogs">🗑 清空记录</button>
        <button class="btn btn-ghost" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchImportLogs, clearImportLogs } from '../api.js'
import { getPlatformInfo, toast } from '../utils.js'

defineEmits(['close'])
const logs = ref([])

function getSourceInfo(source) {
  const platform = source && source.includes(':') ? source.split(':')[0] : source
  return getPlatformInfo(platform)
}

onMounted(async () => { logs.value = await fetchImportLogs() })

async function clearLogs() {
  if (!confirm('确认清空所有导入记录？此操作不可恢复。')) return
  try {
    const res = await clearImportLogs()
    if (res.success) { toast('已清空导入记录', 'success'); logs.value = [] }
    else toast(res.error || '清空失败', 'error')
  } catch (e) { toast('清空请求失败', 'error') }
}
</script>
