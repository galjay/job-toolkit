<template>
  <section class="local-editor">
    <div v-if="stage === 'upload'" class="upload-stage">
      <input ref="fileInput" hidden type="file" accept="image/jpeg,image/png" @change="loadFile" />
      <button class="photo-drop" type="button" @click="fileInput.click()">
        <UploadFilled :size="34" />
        <strong>选择一张正面照片</strong>
        <span>JPG / PNG，最大 8 MB，照片不会上传服务器</span>
      </button>
      <label class="local-ai-toggle"><input v-model="useSegmentation" type="checkbox" />使用浏览器本地人像分割</label>
    </div>

    <div v-else-if="stage === 'processing'" class="processing-stage">
      <span class="spinner" />
      <strong>{{ progress }}</strong>
      <small>首次使用需要加载本地模型，后续会更快。</small>
    </div>

    <div v-else class="editor-layout">
      <div class="canvas-column">
        <div class="canvas-frame" @wheel.prevent="onWheel">
          <canvas
            ref="canvasRef"
            :width="canvasWidth"
            :height="canvasHeight"
            @pointerdown="startDrag"
            @pointermove="moveDrag"
            @pointerup="endDrag"
            @pointerleave="endDrag"
          />
        </div>
        <p>{{ currentSize.label }} · {{ canvasWidth }} × {{ canvasHeight }} px · {{ segmentationLabel }}</p>
        <button class="text-button" type="button" @click="reset">重新选择照片</button>
      </div>

      <div class="control-column">
        <fieldset>
          <legend>背景颜色</legend>
          <div class="color-options">
            <button v-for="color in colors" :key="color.value" type="button" :class="{ active: background === color.value }" :title="color.label" :style="{ '--swatch': color.value }" @click="setBackground(color.value)" />
            <label title="自定义颜色"><input v-model="customColor" type="color" @input="setBackground(customColor)" /></label>
          </div>
        </fieldset>

        <fieldset>
          <legend>照片尺寸</legend>
          <select v-model="size" class="field-input" @change="redraw">
            <option v-for="option in sizes" :key="option.value" :value="option.value">{{ option.label }} · {{ option.mm }}</option>
          </select>
        </fieldset>

        <fieldset>
          <legend>构图调整</legend>
          <label class="range-row"><span>缩放</span><input v-model.number="zoom" type="range" min="1" max="2" step="0.01" @input="redraw" /><b>{{ Math.round(zoom * 100) }}%</b></label>
          <label class="check-row"><input v-model="brighten" type="checkbox" @change="redraw" />轻度提亮</label>
          <small>可直接拖动照片调整人物位置。</small>
        </fieldset>

        <div class="download-actions">
          <button class="secondary-button" type="button" @click="downloadSheet"><Grid :size="16" />六寸排版图</button>
          <button class="primary-button" type="button" @click="downloadSingle"><Download :size="16" />下载单张</button>
        </div>
      </div>
    </div>
    <p v-if="error" class="error-banner">{{ error }}</p>
  </section>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { Download, Grid, UploadFilled } from '@element-plus/icons-vue'


let bodyPixModule = null
const fileInput = ref(null)
const canvasRef = ref(null)
const personImage = ref(null)
const stage = ref('upload')
const progress = ref('正在处理照片')
const error = ref('')
const useSegmentation = ref(true)
const segmentationWorked = ref(false)
const size = ref('one_inch')
const background = ref('#ffffff')
const customColor = ref('#d8ecff')
const zoom = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)
const brighten = ref(false)
const drag = ref(null)
const canvasWidth = ref(295)
const canvasHeight = ref(413)

const sizes = [
  { value: 'one_inch', label: '一寸', mm: '25 × 35 mm', width: 295, height: 413 },
  { value: 'two_inch', label: '二寸', mm: '35 × 49 mm', width: 413, height: 579 },
  { value: 'small_one', label: '小一寸', mm: '22 × 32 mm', width: 260, height: 378 },
  { value: 'exam', label: '考试报名', mm: '33 × 48 mm', width: 390, height: 567 },
]
const colors = [
  { value: '#ffffff', label: '白底' },
  { value: '#438edb', label: '蓝底' },
  { value: '#d94848', label: '红底' },
  { value: '#e8eaed', label: '浅灰底' },
]
const currentSize = computed(() => sizes.find((item) => item.value === size.value) || sizes[0])
const segmentationLabel = computed(() => segmentationWorked.value ? '本地抠图' : '普通裁切')

async function loadFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!/^image\/(jpeg|png)$/.test(file.type) || file.size > 8 * 1024 * 1024) {
    error.value = '请选择 8 MB 以内的 JPG 或 PNG。'
    return
  }
  error.value = ''
  stage.value = 'processing'
  progress.value = useSegmentation.value ? '正在加载本地人像模型' : '正在读取照片'
  const source = await fileToImage(file)
  try {
    personImage.value = useSegmentation.value ? await segmentPerson(source) : source
    segmentationWorked.value = useSegmentation.value
  } catch {
    personImage.value = source
    segmentationWorked.value = false
    error.value = '本地抠图模型不可用，已切换为普通裁切；仍可调整尺寸并下载。'
  }
  stage.value = 'edit'
  await nextTick()
  redraw()
}

function fileToImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = reject
    reader.onload = () => {
      const image = new Image()
      image.onload = () => resolve(image)
      image.onerror = reject
      image.src = reader.result
    }
    reader.readAsDataURL(file)
  })
}

async function segmentPerson(image) {
  progress.value = '正在识别人像轮廓'
  if (!bodyPixModule) bodyPixModule = await import('@tensorflow-models/body-pix')
  await import('@tensorflow/tfjs')
  const network = await bodyPixModule.load({ architecture: 'MobileNetV1', outputStride: 16, multiplier: 0.75, quantBytes: 2 })
  const segmentation = await network.segmentPerson(image, { internalResolution: 'medium', segmentationThreshold: 0.7 })
  const output = document.createElement('canvas')
  output.width = image.naturalWidth || image.width
  output.height = image.naturalHeight || image.height
  const context = output.getContext('2d')
  context.drawImage(image, 0, 0, output.width, output.height)
  const pixels = context.getImageData(0, 0, output.width, output.height)
  for (let index = 0; index < segmentation.data.length; index += 1) {
    if (!segmentation.data[index]) pixels.data[index * 4 + 3] = 0
  }
  context.putImageData(pixels, 0, 0)
  network.dispose?.()
  return output
}

function redraw() {
  const canvas = canvasRef.value
  const source = personImage.value
  if (!canvas || !source) return
  const dimensions = currentSize.value
  canvas.width = dimensions.width
  canvas.height = dimensions.height
  canvasWidth.value = dimensions.width
  canvasHeight.value = dimensions.height
  const context = canvas.getContext('2d')
  context.fillStyle = background.value
  context.fillRect(0, 0, canvas.width, canvas.height)
  const sourceWidth = source.width || source.naturalWidth
  const sourceHeight = source.height || source.naturalHeight
  const scale = Math.max(canvas.width / sourceWidth, canvas.height / sourceHeight) * zoom.value
  const width = sourceWidth * scale
  const height = sourceHeight * scale
  const x = (canvas.width - width) / 2 + canvas.width * offsetX.value / 100
  const y = (canvas.height - height) / 2 + canvas.height * offsetY.value / 100
  context.save()
  if (brighten.value) context.filter = 'brightness(1.07) saturate(1.02)'
  context.drawImage(source, x, y, width, height)
  context.restore()
}

function setBackground(value) { background.value = value; redraw() }
function onWheel(event) { zoom.value = Math.min(2, Math.max(1, zoom.value - Math.sign(event.deltaY) * 0.05)); redraw() }
function startDrag(event) { drag.value = { x: event.clientX, y: event.clientY, offsetX: offsetX.value, offsetY: offsetY.value }; event.currentTarget.setPointerCapture?.(event.pointerId) }
function moveDrag(event) {
  if (!drag.value) return
  offsetX.value = drag.value.offsetX + (event.clientX - drag.value.x) / canvasWidth.value * 100
  offsetY.value = drag.value.offsetY + (event.clientY - drag.value.y) / canvasHeight.value * 100
  redraw()
}
function endDrag() { drag.value = null }

function downloadSingle() { downloadCanvas(canvasRef.value, `标准证件照_${size.value}.png`) }
function downloadSheet() {
  const source = canvasRef.value
  if (!source) return
  const sheet = document.createElement('canvas')
  sheet.width = 1800
  sheet.height = 1200
  const context = sheet.getContext('2d')
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, sheet.width, sheet.height)
  const gap = 30
  const columns = Math.max(1, Math.floor((sheet.width - gap) / (source.width + gap)))
  const rows = Math.max(1, Math.floor((sheet.height - gap) / (source.height + gap)))
  const startX = (sheet.width - (columns * source.width + (columns - 1) * gap)) / 2
  const startY = (sheet.height - (rows * source.height + (rows - 1) * gap)) / 2
  for (let row = 0; row < rows; row += 1) for (let column = 0; column < columns; column += 1) context.drawImage(source, startX + column * (source.width + gap), startY + row * (source.height + gap))
  downloadCanvas(sheet, `六寸排版_${size.value}.png`)
}
function downloadCanvas(canvas, filename) {
  if (!canvas) return
  const link = document.createElement('a')
  link.href = canvas.toDataURL('image/png')
  link.download = filename
  link.click()
}
function reset() { stage.value = 'upload'; personImage.value = null; offsetX.value = 0; offsetY.value = 0; zoom.value = 1; if (fileInput.value) fileInput.value.value = '' }
</script>

<style scoped>
.local-editor { min-height: 430px; }
.upload-stage, .processing-stage { min-height: 400px; display: grid; place-content: center; justify-items: center; gap: 12px; padding: 28px; }
.photo-drop { width: min(500px, 80vw); min-height: 210px; display: grid; place-content: center; justify-items: center; gap: 10px; color: #42505c; background: #f8faf9; border: 1.5px dashed #9fb3aa; border-radius: 8px; }
.photo-drop:hover { border-color: var(--accent); background: var(--accent-soft); }
.photo-drop > svg { width: 34px; height: 34px; }
.photo-drop span, .processing-stage small { color: var(--muted); font-size: 12px; }
.local-ai-toggle, .check-row { display: flex; align-items: center; gap: 8px; color: #4d5964; font-size: 12px; }
.spinner { width: 28px; height: 28px; border: 3px solid #dce7e3; border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.editor-layout { display: grid; grid-template-columns: minmax(320px, 1fr) minmax(280px, .7fr); gap: 28px; padding: 28px; }
.canvas-column { display: grid; justify-items: center; align-content: start; }
.canvas-frame { max-width: 100%; padding: 10px; background: #e5e7e9; border: 1px solid #cbd1d5; touch-action: none; overflow: auto; }
.canvas-frame canvas { display: block; max-width: min(100%, 413px); height: auto; cursor: move; background: white; }
.canvas-column p { margin: 10px 0 0; color: var(--muted); font-size: 11px; }
.control-column { display: flex; flex-direction: column; gap: 20px; }
fieldset { margin: 0; padding: 0 0 18px; border: 0; border-bottom: 1px solid var(--line); }
legend { margin-bottom: 11px; font-size: 13px; font-weight: 750; }
.color-options { display: flex; gap: 9px; align-items: center; }
.color-options button, .color-options label { width: 34px; height: 34px; padding: 3px; background: var(--swatch); border: 1px solid #abb4ba; border-radius: 50%; }
.color-options button.active { outline: 2px solid var(--accent); outline-offset: 2px; }
.color-options input { width: 26px; height: 26px; padding: 0; border: 0; border-radius: 50%; overflow: hidden; }
.range-row { display: grid; grid-template-columns: 45px 1fr 48px; gap: 9px; align-items: center; font-size: 12px; }
.range-row b { text-align: right; }
.check-row { margin-top: 12px; }
fieldset small { display: block; margin-top: 10px; color: var(--muted); font-size: 11px; }
.download-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: auto; }
.download-actions button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
@media (max-width: 800px) { .editor-layout { grid-template-columns: 1fr; padding: 18px; } .download-actions { grid-template-columns: 1fr; } }
</style>
