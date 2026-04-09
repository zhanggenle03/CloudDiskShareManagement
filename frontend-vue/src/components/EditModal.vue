<template>
  <div class="modal-overlay show" @click.self="$emit('close')">
    <div class="modal">
      <h3>✏️ 编辑分享</h3>
      <div class="form-group"><label>文件名称</label><input type="text" v-model="form.name"></div>
      <div class="form-group"><label>提取码</label><input type="text" v-model="form.pwd" placeholder="无提取码则留空"></div>
      <div class="form-group"><label>有效期状态</label>
        <select v-model="form.expire">
          <option>永久有效</option><option>已失效</option><option>7天后失效</option><option>3天后失效</option><option>1天后失效</option>
        </select>
      </div>
      <div class="form-group"><label>标签（逗号分隔）</label><input type="text" v-model="form.tags" placeholder="例：音乐, 电影, 资料"></div>
      <div class="form-group"><label>备注</label><textarea v-model="form.notes" placeholder="添加备注…"></textarea></div>
      <div class="form-group"><label>账号名称</label><input type="text" v-model="form.account_name" placeholder="数据来源账号（最长7字符）" maxlength="7"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="save">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchShare, updateShare } from '../api.js'
import { toast } from '../utils.js'

const props = defineProps({ shareId: Number })
const emit = defineEmits(['close', 'saved'])

const form = ref({ name: '', pwd: '', expire: '永久有效', tags: '', notes: '', account_name: '' })

onMounted(async () => {
  const item = await fetchShare(props.shareId)
  form.value = {
    name: item.name || '', pwd: item.pwd || '', expire: item.expire || '永久有效',
    tags: item.tags || '', notes: item.notes || '', account_name: item.account_name || ''
  }
})

async function save() {
  const res = await updateShare(props.shareId, form.value)
  if (res.success) { toast('保存成功', 'success'); emit('saved') }
  else toast(res.error || '保存失败', 'error')
}
</script>
