<script setup>
import { useI18n } from 'vue-i18n'
import Dialog from '@/components/ui/Dialog.vue'
import { use_restart } from '@/composables/use_restart'

const { t } = useI18n()
const { prompt_open, prompt_title, prompt_message, restarting, restart_bot } = use_restart()
</script>

<template>
  <Dialog
    v-model="prompt_open"
    :title="prompt_title || t('layout.restart_default_title')"
    :description="prompt_message"
    :confirm-text="t('layout.restart_confirm_text')"
    :cancel-text="t('layout.restart_cancel_text')"
    confirm-variant="danger"
    :loading="restarting"
    @confirm="restart_bot"
  />
</template>
