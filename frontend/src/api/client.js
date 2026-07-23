import axios from 'axios'


const api = axios.create({
  baseURL: '/api',
  timeout: 150000,
})

export function apiErrorMessage(error, fallback = '操作失败，请稍后重试') {
  const serverMessage = error?.response?.data?.message
  if (serverMessage) return serverMessage

  if (
    error?.code === 'ECONNABORTED'
    || error?.code === 'ETIMEDOUT'
    || /timeout/i.test(error?.message || '')
  ) {
    return 'AI 处理超时，较长材料可能需要 1-2 分钟，请重试。'
  }

  return error?.message || fallback
}

export default api
