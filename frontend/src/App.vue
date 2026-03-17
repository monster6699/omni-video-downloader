<script setup lang="ts">
import { NMessageProvider, NButton } from 'naive-ui'
import Home from './pages/Home.vue'
</script>

<template>
  <NMessageProvider>
    <div class="min-h-screen flex flex-col">
      <!-- Nav -->
      <nav class="h-16 border-b border-[var(--color-border)] bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-6xl mx-auto h-full px-6 flex items-center justify-between">
          <!-- Logo -->
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-xl bg-[var(--color-primary)] flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </div>
            <span class="text-lg font-bold text-[var(--color-text)]">OmniVideo</span>
            <span class="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-50 text-[var(--color-primary)]">万能视频下载</span>
          </div>

          <!-- Nav Links -->
          <div class="hidden md:flex items-center gap-8 text-sm font-medium text-[var(--color-text-secondary)]">
            <a href="#" class="hover:text-[var(--color-text)] transition-colors">功能特性</a>
            <a href="#" class="hover:text-[var(--color-text)] transition-colors">支持平台</a>
          </div>

          <!-- VIP -->
          <NButton size="small" round :style="{ fontWeight: 600 }">
            <template #icon>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
            </template>
            开通 VIP
          </NButton>
        </div>
      </nav>

      <!-- Main -->
      <main class="flex-1">
        <Home />
      </main>

      <!-- Footer -->
      <footer class="text-center text-[var(--color-text-secondary)] text-xs py-8 border-t border-[var(--color-border)]">
        &copy; 2026 OmniVideo Downloader &middot; 仅供个人学习使用
      </footer>
    </div>
  </NMessageProvider>
</template>
