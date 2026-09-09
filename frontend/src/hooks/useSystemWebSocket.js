import { useState, useEffect, useRef, useCallback } from 'react';

// Force absolute API base URL (guards against empty strings or missing protocol prefixes)
const getApiBaseUrl = () => {
  const rawApiUrl =
    import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (
    rawApiUrl &&
    typeof rawApiUrl === 'string' &&
    rawApiUrl.trim().startsWith('http') &&
    !rawApiUrl.includes('onrender.com')
  ) {
    return rawApiUrl.trim().replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    return window.location.origin;
  }
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

// Derive WebSocket base URL dynamically from API_BASE_URL if VITE_WS_URL is unset
const getWsBaseUrl = () => {
  const rawWsUrl = import.meta.env.VITE_WS_URL;
  if (
    rawWsUrl &&
    typeof rawWsUrl === 'string' &&
    rawWsUrl.trim().startsWith('ws') &&
    !rawWsUrl.includes('onrender.com')
  ) {
    return rawWsUrl.trim().replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && window.location) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}`;
  }
  return API_BASE_URL.replace(/^http/, 'ws');
};

/**
 * Custom hook to handle real-time communications with the Border Surveillance backend.
 */
export function useSystemWebSocket({ onNewAlert } = {}) {
  const [connected, setConnected] = useState(false);
  const [cameraList, setCameraList] = useState([]);
  const [cameraFrames, setCameraFrames] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [systemRunning, setSystemRunning] = useState(true);
  const [status, setStatus] = useState({
    total_cameras: 0,
    cameras_online: 0,
    active_tracks: 0,
    active_alerts: 0,
    last_update: new Date().toISOString(),
    zone_name: 'Border Sector North (Alpha-7)',
  });

  // Keep a stable ref so closures inside WS handlers always call the latest callback
  const onNewAlertRef = useRef(onNewAlert);
  useEffect(() => {
    onNewAlertRef.current = onNewAlert;
  }, [onNewAlert]);

  const alertWsRef = useRef(null);
  const frameWsRefs = useRef({});

  // 1. Fetch camera registry from backend API safely
  const refreshCameras = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/cameras`);

      // Guard: Check if response header is actually JSON before parsing
      const contentType = res.headers.get('content-type');
      if (res.ok && contentType && contentType.includes('application/json')) {
        const data = await res.json();
        const cams = data.cameras || [];
        setCameraList((prev) => {
          if (
            prev.length === cams.length &&
            prev.every((c, i) => c.camera_id === cams[i]?.camera_id && c.enabled === cams[i]?.enabled)
          ) {
            return prev;
          }
          return cams;
        });
        setStatus((prev) => ({
          ...prev,
          total_cameras: cams.length,
          cameras_online: cams.filter((c) => c.enabled !== false).length,
          last_update: new Date().toISOString(),
        }));
      } else {
        console.warn(
          `[Backend Pending] Endpoint ${API_BASE_URL}/api/cameras returned non-JSON response (Server waking up).`
        );
      }
    } catch (err) {
      console.warn(
        `Backend not yet reachable on ${API_BASE_URL}/api/cameras, retrying...`,
        err
      );
    }
  }, []);

  useEffect(() => {
    refreshCameras();
    const interval = setInterval(refreshCameras, 3000);
    return () => clearInterval(interval);
  }, [refreshCameras]);

  // 2. Connect Alert WebSocket directly to backend API URL
  useEffect(() => {
    let reconnectTimer = null;
    const connectAlerts = () => {
      const wsBase = getWsBaseUrl();
      const wsUrl = `${wsBase}/ws/alerts`;

      const ws = new WebSocket(wsUrl);
      alertWsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('[Alert WS] Connected');
        refreshCameras();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'alert' && msg.payload) {
            const payload = msg.payload;
            if (payload.alert_id === 'SYS_CAM_UPDATE') {
              refreshCameras();
              return;
            }
            setAlerts((prev) => [payload, ...prev].slice(0, 50));
            setStatus((prev) => ({
              ...prev,
              active_alerts: prev.active_alerts + 1,
              last_update: new Date().toISOString(),
            }));
            // Fire beep callback for non-system alerts
            if (payload.priority && payload.category !== 'System') {
              onNewAlertRef.current && onNewAlertRef.current(payload);
            }
          } else if (msg.type === 'status' && msg.payload) {
            setStatus((prev) => ({ ...prev, ...msg.payload }));
          }
        } catch (e) {
          console.error('[Alert WS] Failed to parse message:', e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        console.log('[Alert WS] Closed, reconnecting in 3s...');
        reconnectTimer = setTimeout(connectAlerts, 3000);
      };

      ws.onerror = (err) => {
        console.warn('[Alert WS] Error:', err);
        ws.close();
      };
    };

    connectAlerts();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (alertWsRef.current) alertWsRef.current.close();
    };
  }, [refreshCameras]);

  // 3. Connect Frame WebSockets for each camera directly to backend API
  useEffect(() => {
    const activeWsMap = frameWsRefs.current;
    const wsBase = getWsBaseUrl();

    cameraList.forEach((cam) => {
      const cid = cam.camera_id;
      if (
        !activeWsMap[cid] ||
        activeWsMap[cid].readyState === WebSocket.CLOSED
      ) {
        const wsUrl = `${wsBase}/ws/frames/${cid}`;
        const ws = new WebSocket(wsUrl);
        activeWsMap[cid] = ws;

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'frame' && msg.data) {
              setCameraFrames((prev) => ({
                ...prev,
                [cid]: `data:image/jpeg;base64,${msg.data}`,
              }));
            }
          } catch (e) {
            console.error(`[Frame WS ${cid}] Parse error:`, e);
          }
        };

        ws.onerror = () => {};
        ws.onclose = () => {
          delete activeWsMap[cid];
        };
      }
    });

    // Cleanup disconnected cameras
    Object.keys(activeWsMap).forEach((cid) => {
      if (!cameraList.some((c) => c.camera_id === cid)) {
        try {
          activeWsMap[cid].close();
        } catch (e) {}
        delete activeWsMap[cid];
        setCameraFrames((prev) => {
          const next = { ...prev };
          delete next[cid];
          return next;
        });
      }
    });
  }, [cameraList]);

  return {
    connected,
    status,
    alerts,
    setAlerts,
    cameraFrames,
    cameraList,
    refreshCameras,
    systemRunning,
    setSystemRunning,
  };
}
