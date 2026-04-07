/**
 * useEventStream — React hook for the SSE /api/events endpoint.
 *
 * Usage:
 *   const { lastEvent } = useEventStream((event) => {
 *     if (event.event === 'scan.completed') queryClient.invalidateQueries(...)
 *   })
 */

import {useEffect, useRef} from 'react'

export interface SSEEvent {
  event: string
  payload: Record<string, unknown>
  ts: string
}

export function useEventStream(onEvent: (e: SSEEvent) => void) {
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    const es = new EventSource('/api/events')

    es.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data) as SSEEvent
        if (parsed.event !== 'ping') {
          onEventRef.current(parsed)
        }
      } catch {
        // ignore malformed messages
      }
    }

    es.onerror = () => {
      // EventSource auto-reconnects — no action needed
    }

    return () => {
      es.close()
    }
  }, []) // empty deps: connect once per mount
}
