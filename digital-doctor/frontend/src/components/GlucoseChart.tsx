import React from 'react';
import dayjs from 'dayjs';

interface GlucoseDataPoint {
  value_mmol_l: number;
  recorded_at: string;
  measure_type?: string;
}

interface GlucoseChartProps {
  data: GlucoseDataPoint[];
  width?: number;
  height?: number;
}

const TARGET_LOW = 3.9;
const TARGET_HIGH = 10.0;
const Y_MIN = 1.0;
const Y_MAX = 18.0;
const PADDING = { top: 20, right: 20, bottom: 40, left: 50 };

const GlucoseChart: React.FC<GlucoseChartProps> = ({
  data,
  width = 700,
  height = 300,
}) => {
  if (!data || data.length === 0) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
        暂无血糖数据
      </div>
    );
  }

  const sorted = [...data].sort(
    (a, b) => dayjs(a.recorded_at).valueOf() - dayjs(b.recorded_at).valueOf()
  );

  const chartW = width - PADDING.left - PADDING.right;
  const chartH = height - PADDING.top - PADDING.bottom;

  const yRange = Y_MAX - Y_MIN;
  const scaleY = (v: number) => PADDING.top + chartH - ((v - Y_MIN) / yRange) * chartH;

  const xMin = dayjs(sorted[0].recorded_at).valueOf();
  const xMax = dayjs(sorted[sorted.length - 1].recorded_at).valueOf();
  const xRange = xMax - xMin || 1;
  const scaleX = (t: string) => {
    const dx = dayjs(t).valueOf() - xMin;
    return PADDING.left + (dx / xRange) * chartW;
  };

  // Target range shaded area
  const rangeTop = scaleY(TARGET_HIGH);
  const rangeBottom = scaleY(TARGET_LOW);
  const rangeHeight = rangeBottom - rangeTop;

  // Build line path
  const linePath = sorted
    .map((pt, i) => {
      const x = scaleX(pt.recorded_at);
      const y = scaleY(pt.value_mmol_l);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');

  // Y-axis labels
  const yTicks = [2, 4, 6, 8, 10, 12, 14, 16, 18];
  const xTicks = sorted.filter((_, i) => {
    if (sorted.length <= 7) return true;
    const step = Math.ceil(sorted.length / 6);
    return i % step === 0;
  });

  return (
    <svg width={width} height={height} style={{ fontFamily: 'sans-serif' }}>
      {/* Target range shading */}
      <rect
        x={PADDING.left}
        y={rangeTop}
        width={chartW}
        height={rangeHeight}
        fill="#52c41a"
        opacity={0.08}
      />
      <line
        x1={PADDING.left}
        y1={rangeTop}
        x2={PADDING.left + chartW}
        y2={rangeTop}
        stroke="#52c41a"
        strokeWidth={1}
        strokeDasharray="4 2"
        opacity={0.4}
      />
      <line
        x1={PADDING.left}
        y1={rangeBottom}
        x2={PADDING.left + chartW}
        y2={rangeBottom}
        stroke="#52c41a"
        strokeWidth={1}
        strokeDasharray="4 2"
        opacity={0.4}
      />
      <text x={PADDING.left - 6} y={rangeTop + 4} textAnchor="end" fontSize={10} fill="#52c41a">
        10.0
      </text>
      <text x={PADDING.left - 6} y={rangeBottom + 4} textAnchor="end" fontSize={10} fill="#52c41a">
        3.9
      </text>

      {/* Y axis */}
      {yTicks.map((tick) => {
        const y = scaleY(tick);
        return (
          <g key={`y-${tick}`}>
            <line
              x1={PADDING.left}
              y1={y}
              x2={PADDING.left + chartW}
              y2={y}
              stroke="#f0f0f0"
              strokeWidth={1}
            />
            <text x={PADDING.left - 6} y={y + 4} textAnchor="end" fontSize={10} fill="#999">
              {tick}
            </text>
          </g>
        );
      })}

      {/* X axis labels */}
      {xTicks.map((pt) => {
        const x = scaleX(pt.recorded_at);
        const label = dayjs(pt.recorded_at).format(sorted.length > 7 ? 'MM/DD' : 'MM-DD HH:mm');
        return (
          <text key={`x-${pt.recorded_at}`} x={x} y={height - 8} textAnchor="middle" fontSize={10} fill="#999">
            {label}
          </text>
        );
      })}

      {/* Data line */}
      <path d={linePath} fill="none" stroke="#1677ff" strokeWidth={2} strokeLinejoin="round" />

      {/* Data points */}
      {sorted.map((pt, i) => {
        const x = scaleX(pt.recorded_at);
        const y = scaleY(pt.value_mmol_l);
        const isOutOfRange = pt.value_mmol_l < TARGET_LOW || pt.value_mmol_l > TARGET_HIGH;
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r={3.5}
            fill={isOutOfRange ? '#ff4d4f' : '#1677ff'}
            stroke="#fff"
            strokeWidth={1.5}
          />
        );
      })}

      {/* Axis lines */}
      <line
        x1={PADDING.left}
        y1={PADDING.top}
        x2={PADDING.left}
        y2={PADDING.top + chartH}
        stroke="#d9d9d9"
        strokeWidth={1}
      />
      <line
        x1={PADDING.left}
        y1={PADDING.top + chartH}
        x2={PADDING.left + chartW}
        y2={PADDING.top + chartH}
        stroke="#d9d9d9"
        strokeWidth={1}
      />
    </svg>
  );
};

export default GlucoseChart;
