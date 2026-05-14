import axios from 'axios'

function resolveAdminApiKey(): string | null {
  try {
    const fromSession = sessionStorage.getItem('admin_api_key')
    if (fromSession && fromSession.trim()) {
      return fromSession.trim()
    }
  } catch {
    /* ignore */
  }
  const fromEnv = import.meta.env.VITE_ADMIN_API_KEY as string | undefined
  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).trim()
  }
  return null
}

export const adminHttp = axios.create()

adminHttp.interceptors.request.use((config) => {
  const k = resolveAdminApiKey()
  if (k) {
    config.headers.set('X-Admin-API-Key', k)
  }
  return config
})

export function setSessionAdminApiKey(key: string | null) {
  if (!key || !key.trim()) {
    sessionStorage.removeItem('admin_api_key')
    return
  }
  sessionStorage.setItem('admin_api_key', key.trim())
}
