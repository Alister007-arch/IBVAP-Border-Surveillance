/**
 * useAlarmBeep.js
 * ---------------
 * Web Audio API beep synthesiser for IBVAP threat alert notifications.
 *
 * Each priority level has a distinct sound signature:
 *   RED   -- urgent double-burst high-pitched tone (880/1050 Hz square)
 *   AMBER -- single mid-pitched warning beep (520 Hz triangle)
 *   BLUE  -- soft low informational ping (330 Hz sine)
 */

import { useRef, useCallback, useEffect } from 'react';

function getAudioContext() {
  if (!window.__ibvapAudioCtx) {
    try {
      window.__ibvapAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch {
      return null;
    }
  }
  return window.__ibvapAudioCtx;
}

function scheduleBeep(ctx, frequency, duration, startTime, type = 'sine', gainPeak = 0.35) {
  const osc = ctx.createOscillator();
  const gainNode = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(frequency, startTime);
  gainNode.gain.setValueAtTime(0, startTime);
  gainNode.gain.linearRampToValueAtTime(gainPeak, startTime + 0.01);
  gainNode.gain.setValueAtTime(gainPeak, startTime + duration - 0.04);
  gainNode.gain.linearRampToValueAtTime(0, startTime + duration);
  osc.connect(gainNode);
  gainNode.connect(ctx.destination);
  osc.start(startTime);
  osc.stop(startTime + duration);
}

const ALARM_PROFILES = {
  RED: [
    { freq: 880,  dur: 0.12, gap: 0.06, type: 'square',   gain: 0.55 },
    { freq: 1050, dur: 0.14, gap: 0.00, type: 'square',   gain: 0.50 },
  ],
  AMBER: [
    { freq: 520,  dur: 0.22, gap: 0.00, type: 'triangle', gain: 0.42 },
  ],
  BLUE: [
    { freq: 330,  dur: 0.20, gap: 0.00, type: 'sine',     gain: 0.28 },
  ],
};

export function useAlarmBeep() {
  const mutedRef = useRef(false);
  const lastBeepRef = useRef({});

  const ensureResumed = useCallback(async () => {
    const ctx = getAudioContext();
    if (ctx && ctx.state === 'suspended') {
      await ctx.resume();
    }
    return ctx;
  }, []);

  const beep = useCallback(async (priority) => {
    if (mutedRef.current) return;
    const now = Date.now();
    const last = lastBeepRef.current[priority] || 0;
    const throttleMs = priority === 'RED' ? 800 : priority === 'AMBER' ? 1200 : 2000;
    if (now - last < throttleMs) return;
    lastBeepRef.current[priority] = now;

    const ctx = await ensureResumed();
    if (!ctx) return;

    const profile = ALARM_PROFILES[priority] || ALARM_PROFILES.BLUE;
    let t = ctx.currentTime + 0.05;
    profile.forEach(({ freq, dur, gap, type, gain }) => {
      scheduleBeep(ctx, freq, dur, t, type, gain);
      t += dur + gap;
    });
  }, [ensureResumed]);

  const mute = useCallback(() => { mutedRef.current = true; }, []);
  const unmute = useCallback(() => { mutedRef.current = false; }, []);
  const toggleMute = useCallback(() => {
    mutedRef.current = !mutedRef.current;
    return mutedRef.current;
  }, []);

  useEffect(() => {
    const unlock = () => { ensureResumed(); };
    document.addEventListener('click', unlock, { once: true });
    document.addEventListener('keydown', unlock, { once: true });
    return () => {
      document.removeEventListener('click', unlock);
      document.removeEventListener('keydown', unlock);
    };
  }, [ensureResumed]);

  return { beep, mute, unmute, toggleMute };
}
