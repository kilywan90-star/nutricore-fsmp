import { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Tag, Spin, Empty, Alert, Progress } from 'antd';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine, Area, ComposedChart,
} from 'recharts';
import dayjs from 'dayjs';

// ── Types ──────────────────────────────────────────────────────────────

interface CGMSessionItem {
  id: string;
  device_type: string;
  sensor_start: string;
  sensor_end: string | null;
  total_readings: number;
  avg_glucose: number | null;
  estimated_hba1c: number | null;
  cv_percent: number | null;
  time_in_range_pct: number | null;
  time_above_range_pct: number | null;
  time_below_range_pct: number | null;
  time_in_tight_range_pct?: number | null;
  mage?: number | null;
  source_file_name?: string | null;
}

interface HourlyBucket {
  hour: number;
  median: number;
  q1: number;
  q3: number;
  count: number;
}

interface WeeklyTIR {
  week_start: string;
  week_end: string;
  tir_pct: number | null;
  reading_count: number;
}

interface CGMSummary {
  patient_id: string | null;
  days: number;
  has_data: boolean;
  total_readings: number;
  avg_glucose: number | null;
  time_in_range_pct: number;
  time_above_range_pct: number;
  time_below_range_pct: number;
  active_session: {
    id: string;
    device_type: string;
    sensor_start: string;
    avg_glucose: number | null;
    estimated_hba1c: number | null;
    cv_percent: number | null;
  } | null;
  recent_sessions: CGMSessionItem[];
  hourly_profile: Record<string, HourlyBucket>;
  weekly_tir_trend: WeeklyTIR[];
}

interface CGMPattern {
  type: string;
  label: string;
  description: string;
  severity: string;
  recommendation: string;
  details: Record<string, unknown>;
}

interface CGMData {
  summary: CGMSummary | null;
  sessions: CGMSessionItem[];
  patterns: CGMPattern[];
  loading: boolean;
  sessionLoading: boolean;
}

// ── Constants ───────────────────────────────────────────────────────────

const TARGET_LOW = 3.9;
const TARGET_HIGH = 10.0;
const DEVICE_LABELS: Record<string, string> = {
  freestyle_libre: '雅培瞬感',
  dexcom_g6: 'Dexcom G6',
  dexcom_g7: 'Dexcom G7',
  medtronic: '美敦力 Guardian',
  sinocare: '三诺生物',
  microtech: '微泰医疗',
  unknown: '未知设备',
};

const PATTERN_SEVERITY_COLORS: Record<string, string> = {
  info: '#1677ff',
  warning: '#fa8c16',
  critical: '#ff4d4f',
};

// ── Sub-components ─────────────────────────────────────────────────────

function TIRGauge({ pct, label }: { pct: number; label: string }) {
  const color = pct >= 70 ? '#52c41a' : pct >= 50 ? '#faad14' : '#ff4d4f';
  return (
    <div style={{ textAlign: 'center' }}>
      <Progress
        type="dashboard"
        percent={pct}
        format={(p) => `${p}%`}
        strokeColor={color}
        width={120}
        gapDegree={30}
      />
      <div style={{ marginTop: 8, fontSize: 13, color: '#666' }}>{label}</div>
    </div>
  );
}

function HourlyProfileChart({ profile }: { profile: Record<string, HourlyBucket> }) {
  const entries = Object.values(profile).sort((a, b) => a.hour - b.hour);
  if (entries.length === 0) return <Empty description="无数据" />;

  const chartData = entries.map((e) => ({
    hour: `${e.hour}:00`,
    median: e.median,
    q1: e.q1,
    q3: e.q3,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="hour" fontSize={11} interval={2} />
        <YAxis
          domain={[2, 18]}
          ticks={[3.9, 6, 10, 14, 18]}
          fontSize={11}
          label={{ value: 'mmol/L', position: 'insideLeft', offset: 0, fontSize: 11 }}
        />
        <ReferenceLine y={TARGET_LOW} stroke="#fa8c16" strokeDasharray="4 2" strokeWidth={1} label="" />
        <ReferenceLine y={TARGET_HIGH} stroke="#fa8c16" strokeDasharray="4 2" strokeWidth={1} label="" />
        <Tooltip
          formatter={(val: number) => [`${val} mmol/L`, '']}
          labelFormatter={(lbl: string) => `时间: ${lbl}`}
        />
        <Area
          type="monotone"
          dataKey="q3"
          stroke="none"
          fill="#1677ff"
          fillOpacity={0.08}
          name="IQR上限"
        />
        <Area
          type="monotone"
          dataKey="q1"
          stroke="none"
          fill="#1677ff"
          fillOpacity={0.08}
          name="IQR下限"
        />
        <Line
          type="monotone"
          dataKey="median"
          stroke="#1677ff"
          strokeWidth={2.5}
          dot={{ r: 3, fill: '#1677ff' }}
          name="中位数"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function WeeklyTIRChart({ trend }: { trend: WeeklyTIR[] }) {
  const data = trend.map((w) => ({
    week: `${w.week_start.slice(5)}`,
    tir: w.tir_pct,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="week" fontSize={11} />
        <YAxis domain={[0, 100]} ticks={[0, 50, 70, 100]} fontSize={11} />
        <ReferenceLine y={70} stroke="#52c41a" strokeDasharray="4 2" strokeWidth={1} label="目标" />
        <Tooltip formatter={(val: number) => [`${val}%`, 'TIR']} />
        <Line
          type="monotone"
          dataKey="tir"
          stroke="#722ed1"
          strokeWidth={2.5}
          dot={{ r: 4, fill: '#722ed1' }}
          name="TIR"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ── Main Component ─────────────────────────────────────────────────────

interface CGMDashboardProps {
  patientId: string;
}

export default function CGMDashboard({ patientId }: CGMDashboardProps) {
  const [data, setData] = useState<CGMData>({
    summary: null,
    sessions: [],
    patterns: [],
    loading: true,
    sessionLoading: false,
  });

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;

    async function fetchSummary() {
      try {
        const res = await fetch(`/api/v1/doctor/patients/${patientId}/cgm/summary?days=14`);
        if (!res.ok) throw new Error('Failed to fetch');
        const summary = await res.json();
        if (!cancelled) setData((prev) => ({ ...prev, summary, loading: false }));
      } catch {
        if (!cancelled) setData((prev) => ({ ...prev, loading: false }));
      }
    }

    async function fetchSessions() {
      try {
        const res = await fetch(`/api/v1/doctor/patients/${patientId}/cgm/sessions`);
        if (!res.ok) throw new Error('Failed to fetch');
        const sessionsData = await res.json();
        if (!cancelled) setData((prev) => ({ ...prev, sessions: sessionsData.sessions || [], sessionLoading: false }));
      } catch {
        if (!cancelled) setData((prev) => ({ ...prev, sessionLoading: false }));
      }
    }

    async function fetchPatterns() {
      try {
        const res = await fetch(`/api/v1/doctor/patients/${patientId}/cgm/patterns`);
        if (!res.ok) throw new Error('Failed to fetch');
        const patternsData = await res.json();
        if (!cancelled) setData((prev) => ({ ...prev, patterns: patternsData.patterns || [] }));
      } catch { /* ignore */ }
    }

    fetchSummary();
    fetchSessions();
    fetchPatterns();
    return () => { cancelled = true; };
  }, [patientId]);

  if (data.loading) {
    return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;
  }

  const summary = data.summary;

  if (!summary || !summary.has_data) {
    return (
      <Card title="动态血糖监测 (CGM)">
        <Empty description="暂无CGM数据">
          <span style={{ color: '#999', fontSize: 13 }}>
            请导入CGM设备数据（雅培瞬感、Dexcom等）以查看动态血糖报告
          </span>
        </Empty>
      </Card>
    );
  }

  return (
    <div>
      {/* ── AGP Report Cards ── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <TIRGauge pct={summary.time_in_range_pct} label="目标范围内时间 (TIR)" />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="平均血糖"
              value={summary.avg_glucose ?? '-'}
              suffix="mmol/L"
              precision={1}
            />
            <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
              目标: 3.9-10.0 mmol/L
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="GMI (预估HbA1c)"
              value={summary.active_session?.estimated_hba1c ?? '-'}
              suffix="%"
              precision={1}
            />
            <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
              {summary.active_session?.estimated_hba1c && summary.active_session.estimated_hba1c < 7.0
                ? '控制良好'
                : summary.active_session?.estimated_hba1c
                  ? '需改进'
                  : ''}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="CV% (血糖变异系数)"
              value={summary.active_session?.cv_percent ?? '-'}
              suffix="%"
              precision={1}
            />
            <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
              目标: {'<'}36%
            </div>
          </Card>
        </Col>
      </Row>

      {/* ── Range Distribution ── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small" title="高于范围" style={{ borderTop: '3px solid #faad14' }}>
            <Statistic
              value={summary.time_above_range_pct}
              suffix="%"
              precision={1}
              valueStyle={{ color: summary.time_above_range_pct > 25 ? '#ff4d4f' : '#faad14' }}
            />
            <div style={{ fontSize: 12, color: '#999' }}>&gt;10.0 mmol/L</div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" title="在范围内" style={{ borderTop: '3px solid #52c41a' }}>
            <Statistic
              value={summary.time_in_range_pct}
              suffix="%"
              precision={1}
              valueStyle={{ color: summary.time_in_range_pct >= 70 ? '#52c41a' : '#faad14' }}
            />
            <div style={{ fontSize: 12, color: '#999' }}>3.9-10.0 mmol/L</div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" title="低于范围" style={{ borderTop: '3px solid #ff4d4f' }}>
            <Statistic
              value={summary.time_below_range_pct}
              suffix="%"
              precision={1}
              valueStyle={{ color: summary.time_below_range_pct > 4 ? '#ff4d4f' : '#1677ff' }}
            />
            <div style={{ fontSize: 12, color: '#999' }}>&lt;3.9 mmol/L</div>
          </Card>
        </Col>
      </Row>

      {/* ── 24h Glucose Profile ── */}
      <Card title="24小时血糖曲线 (AGP报告)" style={{ marginBottom: 24 }}>
        {Object.keys(summary.hourly_profile || {}).length > 0 ? (
          <HourlyProfileChart profile={summary.hourly_profile} />
        ) : (
          <Empty description="数据不足，需至少1天CGM数据" />
        )}
        <div style={{ marginTop: 8, display: 'flex', gap: 16, color: '#666', fontSize: 12, justifyContent: 'center' }}>
          <span><span style={{ color: '#1677ff', fontWeight: 600 }}>—</span> 中位数</span>
          <span style={{ background: 'rgba(22,119,255,0.08)', padding: '0 8px', borderRadius: 2 }}>IQR四分位范围</span>
          <span><span style={{ color: '#fa8c16' }}>- -</span> 目标范围(3.9-10.0)</span>
        </div>
      </Card>

      {/* ── Weekly TIR Trend ── */}
      {summary.weekly_tir_trend && summary.weekly_tir_trend.length > 0 && (
        <Card title="近4周TIR趋势" style={{ marginBottom: 24 }}>
          <WeeklyTIRChart trend={summary.weekly_tir_trend} />
        </Card>
      )}

      {/* ── Pattern Detection Alerts ── */}
      {data.patterns.length > 0 && (
        <Card title="血糖模式分析" style={{ marginBottom: 24 }}>
          {data.patterns.map((p, i) => (
            <Alert
              key={i}
              type={p.severity === 'warning' ? 'warning' : 'info'}
              showIcon
              message={
                <span>
                  <Tag color={PATTERN_SEVERITY_COLORS[p.severity] || '#1677ff'}>{p.label}</Tag>
                  {p.description}
                </span>
              }
              description={
                <div style={{ fontSize: 13, color: '#666', marginTop: 4 }}>
                  <strong>建议: </strong>{p.recommendation}
                </div>
              }
              style={{ marginBottom: 12 }}
            />
          ))}
        </Card>
      )}

      {/* ── Sessions History ── */}
      {data.sessions.length > 1 && (
        <Card title="历史CGM会话" size="small">
          {data.sessions.slice(0, 10).map((s) => (
            <div
              key={s.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 0',
                borderBottom: '1px solid #f0f0f0',
                fontSize: 13,
              }}
            >
              <span>
                <Tag>{DEVICE_LABELS[s.device_type] || s.device_type}</Tag>
                {dayjs(s.sensor_start).format('YYYY-MM-DD')}
                {s.sensor_end ? ` ~ ${dayjs(s.sensor_end).format('YYYY-MM-DD')}` : ' (进行中)'}
              </span>
              <span style={{ color: '#666' }}>
                {s.total_readings}条 | 平均{s.avg_glucose} mmol/L
                {s.time_in_range_pct != null && ` | TIR ${s.time_in_range_pct}%`}
              </span>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
