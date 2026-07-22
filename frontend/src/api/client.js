import axios from 'axios'


const api = axios.create({
  baseURL: '/api',
  timeout: 70000,
})

export function apiErrorMessage(error, fallback = '操作失败，请稍后重试') {
  return error?.response?.data?.message || error?.message || fallback
}

export default api
