<template>
  <div class="modal-overlay show" @click.self="$emit('close')">
    <div class="modal" style="width:400px;text-align:center;padding:32px;">
      <div style="width:80px;height:80px;margin:0 auto 20px;border-radius:18px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,0.12);display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#4F6EF7,#7B5EA7);font-size:36px;">☁️</div>
      <h3 style="margin-bottom:20px;font-size:22px;font-weight:700;">网盘分享管理</h3>
      <div style="text-align:left;background:var(--bg);border-radius:14px;padding:20px;margin-bottom:24px;border:1px solid var(--gray-100);">
        <div style="display:flex;align-items:center;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid var(--gray-100);">
          <span style="color:var(--gray-500);width:70px;flex-shrink:0;font-size:13px;">作者</span>
          <span style="color:var(--text);font-size:13px;">Dropstar</span>
        </div>
        <div style="display:flex;align-items:flex-start;">
          <span style="color:var(--gray-500);width:70px;flex-shrink:0;font-size:13px;margin-top:2px;">项目地址</span>
          <a href="https://github.com/zhanggenle03/CloudDiskShareManagement" target="_blank" style="color:var(--primary);font-size:12px;word-break:break-all;text-decoration:none;">https://github.com/zhanggenle03/CloudDiskShareManagement</a>
        </div>
      </div>
      <button class="btn btn-primary" @click="$emit('close')" style="min-width:120px;padding:10px 32px;">确定</button>
    </div>
  </div>
</template>

<script setup>
defineEmits(['close'])
</script>
