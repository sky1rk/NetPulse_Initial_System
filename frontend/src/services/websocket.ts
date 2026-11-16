/** WebSocket helper with bounded reconnect.

The dashboard also polls its monitoring session while live updates are
unavailable, so a dropped socket never leaves stale data silently on screen.
*/

import { useEffect, useRef, useState } from "react";
import { WS_BASE } from "./api";

export type SocketStatus = "connecting" | "live" | "offline";

export function useMonitoringSocket(onEvent: (payload: Record<string, unknown>) => void) {
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let attempt = 0;

    const connect = () => {
      if (stopped) return;
      setStatus("connecting");
      try {
        socket = new WebSocket(`${WS_BASE}/ws/monitoring`);
      } catch {
        setStatus("offline");
        return;
      }
      socket.onopen = () => {
        attempt = 0;
        setStatus("live");
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data as string) as Record<string, unknown>;
          handlerRef.current(payload);
        } catch {
          // Ignore malformed server messages.
        }
      };
      socket.onerror = () => {
        socket?.close();
      };
      socket.onclose = () => {
        if (stopped) return;
        setStatus("offline");
        attempt += 1;
        const delay = Math.min(15000, 1000 * attempt);
        retryTimer = window.setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      stopped = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return { status };
}
