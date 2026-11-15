<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { useThemeStore } from '@/stores/theme'

// 按需注册：柱状/折线 + 网格/图例/提示框 + Canvas 渲染
use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  /** 数据项：[{ label: '2026-08-24', ...series.key ]} */
  items: { type: Array, required: true },
  /** 序列定义：[{ key: 'received', name: '接收', color: '#2563eb' }] */
  series: { type: Array, required: true },
  /** 图表类型：bar | line */
  type: {
    type: String,
    default: 'bar',
    validator: (value) => ['bar', 'line'].includes(value),
  },
})

const { is_dark } = storeToRefs(useThemeStore())

/** ECharts 用 canvas 渲染，颜色需为字面量，无法解析 CSS 变量 */
const chart_palette = computed(() =>
  is_dark.value
    ? {
        text: '#e7e7ea',
        axis_line: '#4a4b56',
        split_line: '#2e2f37',
        tooltip_bg: '#33343d',
        tooltip_border: '#4a4b56',
        tooltip_text: '#e7e7ea',
      }
    : {
        text: '#71717a',
        axis_line: '#e4e4e7',
        split_line: '#e4e4e7',
        tooltip_bg: '#ffffff',
        tooltip_border: '#e4e4e7',
        tooltip_text: '#18181b',
      },
)

const chart_option = computed(() => ({
  grid: { left: 44, right: 12, top: 28, bottom: 24 },
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
    confine: true,
    backgroundColor: chart_palette.value.tooltip_bg,
    borderColor: chart_palette.value.tooltip_border,
    textStyle: { color: chart_palette.value.tooltip_text },
  },
  legend: {
    top: 0,
    left: 'center',
    icon: 'roundRect',
    itemWidth: 10,
    itemHeight: 10,
    textStyle: { color: chart_palette.value.text, fontSize: 12 },
  },
  xAxis: {
    type: 'category',
    data: props.items.map((item) => item.label),
    axisTick: { show: false },
    axisLine: { lineStyle: { color: chart_palette.value.axis_line } },
    axisLabel: {
      color: chart_palette.value.text,
      fontSize: 10,
      // 标签格式化为 MM-DD，并抽样避免重叠
      formatter: (value) => value.slice(5),
      interval: Math.max(0, Math.ceil(props.items.length / 8) - 1),
    },
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: chart_palette.value.split_line } },
    axisLabel: { color: chart_palette.value.text, fontSize: 10 },
  },
  series: props.series.map((serie) => ({
    name: serie.name,
    type: props.type,
    data: props.items.map((item) => Number(item[serie.key]) || 0),
    ...(props.type === 'line'
      ? {
          color: serie.color,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 2 },
          emphasis: { focus: 'series' },
        }
      : {
          itemStyle: { color: serie.color, borderRadius: [2, 2, 0, 0] },
          barMaxWidth: 14,
        }),
  })),
}))
</script>

<template>
  <VChart class="trend-chart" :option="chart_option" autoresize />
</template>

<style scoped>
.trend-chart {
  width: 100%;
  height: 260px;
}
</style>
