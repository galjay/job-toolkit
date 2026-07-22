<template>
  <div class="app-shell">
    <header class="app-header">
      <router-link to="/" class="brand" aria-label="求职工具箱首页">
        <span class="brand-mark">求</span>
        <span>
          <strong>求职工具箱</strong>
          <small>本地开源版</small>
        </span>
      </router-link>

      <nav class="main-nav" aria-label="主要工具">
        <router-link to="/">
          <Document :size="18" />
          <span>简历与 JD</span>
        </router-link>
        <router-link to="/photo">
          <PictureFilled :size="18" />
          <span>证件照</span>
        </router-link>
      </nav>

      <span class="local-status"><i />本地运行</span>
    </header>

    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { Document, PictureFilled } from '@element-plus/icons-vue'
</script>
