/** API 客户端 */
import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export default client
