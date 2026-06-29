import { useEffect, useRef, useState } from 'react'

export interface PollingState<T> {
  data: T | null
  error: Error | null
  loading: boolean
}

export function usePolling<T>(
  fn: () => Promise<T>,
  intervalMs: number,
  deps: unknown[] = [],
): PollingState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const fnRef = useRef(fn)
  fnRef.current = fn

  useEffect(() => {
    let active = true
    const tick = async () => {
      try {
        const result = await fnRef.current()
        if (active) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (active) setError(err as Error)
      } finally {
        if (active) setLoading(false)
      }
    }
    tick()
    const id = setInterval(tick, intervalMs)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [intervalMs, ...deps])

  return { data, error, loading }
}
