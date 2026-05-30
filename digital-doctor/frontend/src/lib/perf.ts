/**
 * Web Vitals reporting — LCP, FID, CLS
 * Reports metrics to analytics endpoint and console for dev.
 */

interface MetricEntry {
  name: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  id: string;
}

const ANALYTICS_ENDPOINT = '/api/v1/analytics/web-vitals';

// ── Rating thresholds ─────────────────────────────────────────────────
const thresholds: Record<string, [number, number]> = {
  LCP: [2500, 4000], // good < 2.5s, poor > 4s
  FID: [100, 300],   // good < 100ms, poor > 300ms
  CLS: [0.1, 0.25],  // good < 0.1, poor > 0.25
  FCP: [1800, 3000], // good < 1.8s, poor > 3s
  TTFB: [800, 1800], // good < 800ms, poor > 1.8s
};

function getRating(name: string, value: number): MetricEntry['rating'] {
  const [good, poor] = thresholds[name] || [Infinity, Infinity];
  if (value <= good) return 'good';
  if (value <= poor) return 'needs-improvement';
  return 'poor';
}

function sendToAnalytics(entry: MetricEntry): void {
  // Fire-and-forget — don't block the main thread
  if (navigator.sendBeacon) {
    const data = JSON.stringify(entry);
    navigator.sendBeacon(ANALYTICS_ENDPOINT, new Blob([data], { type: 'application/json' }));
  }
}

function reportMetric(metric: MetricEntry): void {
  if (import.meta.env.DEV) {
    console.log(`[Perf] ${metric.name}: ${metric.value} (${metric.rating})`);
  }
  sendToAnalytics(metric);
}

// ── Page render time tracking ─────────────────────────────────────────
const pageTimers = new Map<string, number>();

export function startPageTimer(pageName: string): void {
  pageTimers.set(pageName, performance.now());
}

export function endPageTimer(pageName: string): void {
  const start = pageTimers.get(pageName);
  if (!start) return;
  const duration = performance.now() - start;
  pageTimers.delete(pageName);

  const entry: MetricEntry = {
    name: `page_render_${pageName}`,
    value: Math.round(duration),
    rating: duration < 1000 ? 'good' : duration < 3000 ? 'needs-improvement' : 'poor',
    delta: duration,
    id: `page-${pageName}-${Date.now()}`,
  };
  reportMetric(entry);

  if (import.meta.env.DEV) {
    console.log(`[Perf] Page "${pageName}" rendered in ${Math.round(duration)}ms`);
  }
}

// ── Web Vitals observation ────────────────────────────────────────────
export function initWebVitals(): void {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) return;

  // LCP
  try {
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length === 0) return;
      const lastEntry = entries[entries.length - 1] as PerformanceEntry & { startTime: number };
      const entry: MetricEntry = {
        name: 'LCP',
        value: Math.round(lastEntry.startTime),
        rating: getRating('LCP', lastEntry.startTime),
        delta: lastEntry.startTime,
        id: `lcp-${Date.now()}`,
      };
      reportMetric(entry);
    });
    lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (_) { /* not supported */ }

  // FID
  try {
    const fidObserver = new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        const fidEntry = e as PerformanceEventTiming;
        if (fidEntry.processingStart > 0) {
          const entry: MetricEntry = {
            name: 'FID',
            value: Math.round(fidEntry.processingStart - fidEntry.startTime),
            rating: getRating('FID', fidEntry.processingStart - fidEntry.startTime),
            delta: fidEntry.processingStart - fidEntry.startTime,
            id: `fid-${Date.now()}`,
          };
          reportMetric(entry);
        }
      }
    });
    fidObserver.observe({ type: 'first-input', buffered: true });
  } catch (_) { /* not supported */ }

  // CLS
  try {
    let clsValue = 0;
    const clsObserver = new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        const clsEntry = e as PerformanceEntry & { hadRecentInput: boolean; value: number };
        if (!clsEntry.hadRecentInput) {
          clsValue += clsEntry.value;
        }
      }
      const entry: MetricEntry = {
        name: 'CLS',
        value: Math.round(clsValue * 1000) / 1000,
        rating: getRating('CLS', clsValue),
        delta: clsValue,
        id: `cls-${Date.now()}`,
      };
      reportMetric(entry);
    });
    clsObserver.observe({ type: 'layout-shift', buffered: true });
  } catch (_) { /* not supported */ }
}
