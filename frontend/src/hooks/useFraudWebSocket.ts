import { useEffect, useRef, useState } from 'react';
import { AlertRecord, ScoredTransaction } from '../types';

interface UseFraudWebSocketProps {
  onTransaction?: (tx: ScoredTransaction) => void;
  onAlertCreated?: (alert: AlertRecord) => void;
  onAlertUpdated?: (alert: AlertRecord) => void;
}

export function useFraudWebSocket({ onTransaction, onAlertCreated, onAlertUpdated }: UseFraudWebSocketProps) {
  const [connected, setConnected] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    const connect = () => {
      if (!active) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/live`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (active) setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'TRANSACTION_SCORED' && onTransaction) {
            onTransaction(msg.data);
          } else if (msg.type === 'ALERT_CREATED' && onAlertCreated) {
            onAlertCreated(msg.data);
          } else if (msg.type === 'ALERT_UPDATED' && onAlertUpdated) {
            onAlertUpdated(msg.data);
          }
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = () => {
        if (!active) return;
        setConnected(false);
        reconnectTimerRef.current = window.setTimeout(connect, 2500);
      };
    };

    connect();
    return () => {
      active = false;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { connected };
}
