<template>
  <div class="modal-overlay show" @click.self="$emit('close')">
    <!-- 步骤1: 选择文件 -->
    <div v-if="step === 'select'" class="modal" style="width:480px">
      <h3>📥 导入数据</h3>
      <div class="import-zone-modal" :class="{ dragover }" @click="fileInput.click()" @dragover.prevent="dragover=true" @dragleave="dragover=false" @drop.prevent="onDrop">
        <div class="icon">📂</div>
        <p><b>点击选择</b> 或将CSV文件拖拽到此处</p>
        <p style="margin-top:4px;color:var(--gray-400);font-size:12px;">支持百度网盘 / 夸克网盘导出的分享记录CSV，可多选</p>
        <input type="file" ref="fileInput" accept=".csv" multiple @change="onFileInput" style="display:none">
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" @click="$emit('close')">关闭</button>
      </div>
    </div>
    <!-- 步骤2: 配置账号名 -->
    <div v-else class="modal" style="width:520px;max-height:80vh;display:flex;flex-direction:column;">
      <h3>📋 设置文件账号</h3>
      <p style="font-size:12px;color:var(--gray-500);margin:-4px 0 10px;">为每个导入的文件指定数据来源账号（可选）</p>
      <div style="flex:1;overflow-y:auto;min-height:0;">
        <div v-for="(f, i) in pendingFiles" :key="i" style="display:flex;align-items:center;gap:10px;padding:8px 4px;border-bottom:1px solid var(--gray-100);">
          <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:500;">📄 {{ f.name }}</span>
          <input type="text" v-model="accountNames[i]" placeholder="可选（最长7字符）" maxlength="7"
            style="width:130px;padding:5px 8px;border:1.5px solid var(--border);border-radius:6px;font-size:12px;outline:none;background:var(--bg);">
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:12px;padding-top:10px;border-top:1px solid var(--gray-100);">
        <button class="btn btn-primary" @click="doImport" style="flex:1;">确认并导入</button>
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { importCsv } from '../api.js'
import { toast } from '../utils.js'

const emit = defineEmits(['close', 'imported'])

const step = ref('select')
const pendingFiles = ref([])
const accountNames = ref([])
const dragover = ref(false)
const fileInput = ref(null)

function onFileInput(e) {
  const files = e.target.files
  if (files.length) handleFiles(files)
  e.target.value = ''
}

function onDrop(e) {
  dragover.value = false
  const files = e.dataTransfer.files
  if (files.length) handleFiles(files)
}

function handleFiles(files) {
  const csvFiles = Array.from(files).filter(f => f.name.endsWith('.csv'))
  if (csvFiles.length === 0) { toast('请上传CSV文件', 'error'); return }
  pendingFiles.value = csvFiles
  accountNames.value = csvFiles.map(() => '')
  step.value = 'config'
}

async function doImport() {
  const files = pendingFiles.value
  if (!files.length) return
  toast(`正在导入 ${files.length} 个文件…`, 'info')
  let totalImported = 0, totalSkipped = 0, failCount = 0
  for (let i = 0; i < files.length; i++) {
    const fd = new FormData()
    fd.append('file', files[i])
    const accountName = (accountNames.value[i] || '').trim()
    if (accountName) fd.append('account_name', accountName)
    try {
      const res = await importCsv(fd)
      if (res.success) { totalImported += res.imported; totalSkipped += res.skipped }
      else { failCount++; toast(`${files[i].name}: ${res.error || '导入失败'}`, 'error') }
    } catch (e) { failCount++ }
  }
  if (failCount === 0) toast(`全部导入完成：新增 ${totalImported} 条，更新 ${totalSkipped} 条`, 'success')
  else toast(`部分导入完成：成功 ${files.length - failCount}/${files.length}`, 'warning')
  emit('imported')
}
</script>
