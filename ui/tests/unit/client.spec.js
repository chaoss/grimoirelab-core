import { afterEach, describe, expect, test, vi } from 'vitest'
import { AxiosError } from 'axios'
import { client } from '@/services/api/client'

const logOutUser = vi.fn()

vi.mock('@/router', () => ({
  default: { currentRoute: { value: { fullPath: '/projects', query: {} } } }
}))
vi.mock('@/store', () => ({
  useUserStore: () => ({ logOutUser })
}))

const onRejected = client.interceptors.response.handlers[0].rejected

describe('services/api/client', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  test('Logs out the user when the credentials are missing', async () => {
    const error = new AxiosError('Request failed with status code 403')
    error.response = {
      status: 403,
      data: { detail: 'Authentication credentials were not provided.' }
    }

    await expect(onRejected(error)).rejects.toBe(error)
    expect(logOutUser).toHaveBeenCalledWith({ redirect: '/projects' })
  })

  test('Rejects with the original error when there is no response', async () => {
    const error = new AxiosError('Network Error', AxiosError.ERR_NETWORK)

    await expect(onRejected(error)).rejects.toBe(error)
    expect(logOutUser).not.toHaveBeenCalled()
  })

  test('Rejects with the original error when the response has no data', async () => {
    const error = new AxiosError('Request failed with status code 403')
    error.response = { status: 403 }

    await expect(onRejected(error)).rejects.toBe(error)
    expect(logOutUser).not.toHaveBeenCalled()
  })
})
