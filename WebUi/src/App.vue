<script setup>
import { ConfigProvider, TooltipProvider } from 'reka-ui'
import { RouterView } from 'vue-router'
import Toast from '@/components/ui/Toast.vue'
</script>

<template>
  <ConfigProvider>
    <TooltipProvider :delay-duration="200">
      <RouterView />
    </TooltipProvider>
    <Toast />
  </ConfigProvider>
</template>
