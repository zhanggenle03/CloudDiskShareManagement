<template>
  <div class="modal-overlay show" @click.self="$emit('close')">
    <div class="modal">
      <h3>🏷️ 批量添加标签</h3>
      <div class="form-group">
        <label>标签名称</label>
        <input type="text" v-model="tagName" placeholder="输入标签名" @input="onInput">
      </div>
      <div v-if="tagName.trim()" class="form-group">
        <label>标签颜色</label>
        <div class="color-picker-grid">
          <div v-for="c in PRESET_COLORS" :key="c" class="color-swatch" :class="{ selected: selectedColor === c }"
            :style="{ background: c }" @click="selectedColor = c"></div>
        </div>
        <div class="color-custom-row">
          <input type="color" v-model="customColor"><label>自定义颜色</label>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="doBatchTag">确认添加</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { batchTagShares, setTagColor } from '../api.js'
import { PRESET_COLORS, toast } from '../utils.js'
import { store } from '../store.js'

const props = defineProps({ selectedIds: Array })
const emit = defineEmits(['close', 'done'])

const tagName = ref('')
const selectedColor = ref('')
const customColor = ref('#4F6EF7')

function onInput() {
  const existingColor = store.tagColors[tagName.value.trim()]
  if (existingColor && !selectedColor.value) {
    selectedColor.value = existingColor
    customColor.value = existingColor
  }
}

async function doBatchTag() {
  const tag = tagName.value.trim()
  if (!tag) { toast('请输入标签名', 'warning'); return }
  const color = PRESET_COLORS.includes(selectedColor.value) ? selectedColor.value : customColor.value
  await batchTagShares(props.selectedIds, tag, 'add')
  if (color) {
    await setTagColor(tag, color)
    store.tagColors[tag] = color
  }
  toast(`已为 ${props.selectedIds.length} 条添加标签「${tag}」`, 'success')
  emit('done')
}
</script>
