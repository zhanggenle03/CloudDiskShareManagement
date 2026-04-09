<template>
  <div class="modal-overlay show" @click.self="$emit('close')">
    <div class="modal" style="width:800px;height:600px;max-height:85vh;display:flex;flex-direction:column;">
      <h3>👤 网盘账号管理</h3>
      <div style="display:flex;gap:16px;margin-top:12px;flex:1;min-height:0;">
        <!-- 左侧：平台选择 -->
        <div style="width:140px;flex-shrink:0;display:flex;flex-direction:column;">
          <div style="font-size:13px;color:var(--gray-500);margin-bottom:8px;">选择网盘</div>
          <div class="account-platform-list">
            <div class="account-platform-item" :class="{ active: currentPlatform === 'quark' }" @click="switchPlatform('quark')"><span>🟣 夸克网盘</span></div>
            <div class="account-platform-item" :class="{ active: currentPlatform === 'baidu' }" @click="switchPlatform('baidu')"><span>🔵 百度网盘</span></div>
          </div>
        </div>
        <!-- 右侧：账号列表 -->
        <div style="flex:1;min-width:0;display:flex;flex-direction:column;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <div style="font-size:14px;font-weight:600;color:var(--text);">{{ currentPlatform === 'quark' ? '夸克网盘账号' : '百度网盘账号' }}</div>
            <button class="btn btn-primary" @click="showAddForm = true" style="padding:5px 14px;font-size:12px;">+ 添加账号</button>
          </div>
          <div style="flex:1;overflow-y:auto;border:1.5px solid var(--border);border-radius:8px;">
            <div v-if="accounts.length === 0" style="text-align:center;padding:50px 20px;color:var(--gray-400);">
              <div style="font-size:32px;margin-bottom:10px;">📭</div>暂无账号，点击上方"添加账号"开始
            </div>
            <table v-else class="account-table">
              <thead><tr><th style="width:120px;">账号名称</th><th>备注</th><th style="width:90px;">状态</th><th style="width:150px;">操作</th></tr></thead>
              <tbody>
                <tr v-for="acc in accounts" :key="acc.id">
                  <td style="font-weight:600;" :title="acc.name">{{ acc.name.length > 7 ? acc.name.substring(0, 7) + '...' : acc.name }}</td>
                  <td style="color:var(--text-secondary);font-size:12px;">{{ acc.remark || '-' }}</td>
                  <td>
                    <span class="account-status" :class="getStatusClass(acc)">{{ getStatusText(acc) }}</span>
                  </td>
                  <td class="account-actions" style="white-space:nowrap;">
                    <button class="btn btn-ghost" @click="startEdit(acc)">✏️ 编辑</button>
                    <button v-if="acc.cookie && acc.cookie.length >= 50" class="btn btn-ghost" @click="testCookie(acc.id)" :disabled="testingId === acc.id">{{ testingId === acc.id ? '⏳ 验证中...' : '🧪 验证' }}</button>
                    <button v-else class="btn btn-ghost" disabled style="opacity:0.5;cursor:not-allowed;">🧪 验证</button>
                    <button class="btn btn-danger" @click="doDelete(acc)">🗑️</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <!-- 添加账号弹窗 -->
      <div v-if="showAddForm" class="modal-overlay show" style="position:absolute;" @click.self="showAddForm = false">
        <div class="modal" style="width:440px;">
          <h3>➕ 添加账号</h3>
          <div class="form-group">
            <label>账号名称 <span style="font-size:11px;color:var(--gray-500);">{{ newName.length }}/7</span></label>
            <input type="text" v-model="newName" maxlength="7" placeholder="账号名称">
          </div>
          <div class="form-group">
            <label>Cookie <span style="font-size:11px;color:var(--gray-400);">可选</span></label>
            <input type="password" v-model="newCookie" placeholder="粘贴网盘Cookie">
          </div>
          <div class="form-group">
            <label>备注 <span style="font-size:11px;color:var(--gray-500);">{{ newRemark.length }}/50</span></label>
            <textarea v-model="newRemark" maxlength="50" placeholder="备注（可选）" style="min-height:60px;"></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn btn-ghost" @click="showAddForm = false">取消</button>
            <button class="btn btn-primary" @click="addAccount">✓ 添加</button>
          </div>
        </div>
      </div>
      <!-- 编辑账号弹窗 -->
      <div v-if="showEditForm" class="modal-overlay show" style="position:absolute;" @click.self="showEditForm = false">
        <div class="modal" style="width:440px;">
          <h3>✏️ 编辑账号</h3>
          <div class="form-group">
            <label>账号名称 <span style="font-size:11px;color:var(--gray-500);">{{ editForm.name.length }}/7</span></label>
            <input type="text" v-model="editForm.name" maxlength="7">
          </div>
          <div class="form-group">
            <label>Cookie <span style="font-size:11px;color:var(--gray-400);">{{ editForm.hasCookie ? '已保存，留空不修改' : '留空则不设置' }}</span></label>
            <input type="password" v-model="editForm.cookie" :placeholder="editForm.hasCookie ? 'Cookie已保存 (直接保存新值可更新)' : '粘贴网盘Cookie'">
          </div>
          <div class="form-group">
            <label>备注 <span style="font-size:11px;color:var(--gray-500);">{{ editForm.remark.length }}/50</span></label>
            <textarea v-model="editForm.remark" maxlength="50" style="min-height:60px;"></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn btn-ghost" @click="showEditForm = false">取消</button>
            <button class="btn btn-primary" @click="saveEdit">💾 保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { fetchAccounts, createAccount, updateAccount, deleteAccount, testAccountCookie } from '../api.js'
import { toast } from '../utils.js'

defineEmits(['close'])

const currentPlatform = ref('quark')
const accounts = ref([])
const showAddForm = ref(false)
const showEditForm = ref(false)
const testingId = ref(null)
const newName = ref('')
const newCookie = ref('')
const newRemark = ref('')
const editForm = ref({ id: null, name: '', cookie: '', remark: '', hasCookie: false })

function getStatusClass(acc) {
  if (acc.is_valid === 1) return 'valid'
  if (acc.is_valid === -1) return 'invalid'
  if (!acc.cookie || acc.cookie.length < 50) return 'unknown'
  return 'unknown'
}

function getStatusText(acc) {
  if (acc.is_valid === 1) return '✅ 已验证'
  if (acc.is_valid === -1) return '❌ 已失效'
  if (!acc.cookie || acc.cookie.length < 50) return '⚠️ 未配置'
  return '⚠️ 未验证'
}

async function switchPlatform(p) {
  currentPlatform.value = p
  await loadAccounts()
}

async function loadAccounts() {
  accounts.value = await fetchAccounts(currentPlatform.value)
}

onMounted(() => loadAccounts())

async function addAccount() {
  const name = newName.value.trim()
  if (!name) { toast('请输入账号名称', 'warning'); return }
  if (name.length > 7) { toast('账号名称不能超过7个字', 'warning'); return }
  const cookie = newCookie.value.trim()
  if (cookie && cookie.length < 50) { toast('Cookie格式不正确，请检查是否完整', 'warning'); return }
  try {
    const res = await createAccount({ platform: currentPlatform.value, name, cookie, remark: newRemark.value.trim() })
    if (res.success) { toast('账号添加成功', 'success'); showAddForm.value = false; newName.value = ''; newCookie.value = ''; newRemark.value = ''; loadAccounts() }
    else toast(res.error || '添加失败', 'error')
  } catch (e) { toast('添加失败', 'error') }
}

function startEdit(acc) {
  editForm.value = {
    id: acc.id, name: acc.name, cookie: '', remark: acc.remark || '',
    hasCookie: acc.cookie && acc.cookie.length >= 50
  }
  showEditForm.value = true
}

async function saveEdit() {
  const { id, name, cookie, remark } = editForm.value
  if (!name.trim()) { toast('账号名称不能为空', 'warning'); return }
  const fields = { name: name.trim(), remark: remark.trim() }
  if (cookie.trim()) { fields.cookie = cookie.trim(); fields.is_valid = 0 }
  try {
    const res = await updateAccount(id, fields)
    if (res.success) { toast('账号更新成功', 'success'); showEditForm.value = false; loadAccounts() }
    else toast(res.error || '更新失败', 'error')
  } catch (e) { toast('更新失败', 'error') }
}

async function testCookie(id) {
  testingId.value = id
  try {
    const res = await testAccountCookie(id)
    if (res.valid) toast(res.message || 'Cookie有效', 'success')
    else toast(res.message || 'Cookie无效', 'error')
    loadAccounts()
  } catch (e) { toast('验证请求失败', 'error') }
  finally { testingId.value = null }
}

async function doDelete(acc) {
  if (!confirm(`确认删除账号"${acc.name}"？此操作不可恢复。`)) return
  try {
    const res = await deleteAccount(acc.id)
    if (res.success) { toast('账号已删除', 'success'); loadAccounts() }
    else toast(res.error || '删除失败', 'error')
  } catch (e) { toast('删除失败', 'error') }
}
</script>
