<template>
  <router-view />
</template>

<script setup lang="ts">
// 根组件，基于路由渲染不同页面
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

body {
  color: #1f3448;
  background: #f3f6fa;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

button,
input,
textarea,
select {
  font: inherit;
}

.el-card {
  border-color: #dfe8ef;
}

.el-table {
  --el-table-header-bg-color: #f7fafc;
  --el-table-header-text-color: #47596a;
}
</style>
