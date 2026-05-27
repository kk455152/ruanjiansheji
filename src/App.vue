<script setup>
import { ElMessage } from 'element-plus'

function showMessage() {
  ElMessage.success('Element Plus is working.')
}
</script>

<template>
  <main class="page">
    <section class="panel">
      <el-tag type="success" effect="dark">Element Plus</el-tag>
      <h1>Element Plus is ready.</h1>
      <p class="copy">
        Vue can now use Element Plus components in this project.
      </p>
      <el-button class="action" type="primary" @click="showMessage">
        Test Element Plus
      </el-button>
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  margin: 0;
  background: #f4f7fb;
  color: #1f2937;
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}

.panel {
  width: min(560px, calc(100vw - 32px));
  padding: 32px;
  border: 1px solid #d8e0ec;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 48px rgba(31, 41, 55, 0.08);
}

h1 {
  margin: 16px 0 0;
  font-size: 32px;
  line-height: 1.15;
}

.copy {
  margin: 16px 0 0;
  color: #4b5563;
  font-size: 16px;
  line-height: 1.6;
}

.action {
  margin-top: 20px;
}
</style>
