"use client";

import { useState, useEffect } from "react";

interface ReceptionRecord {
  id: number;
  sessionId: string;
  date: string;
  city: string;
  guestName: string;
  guestLevel: string;
  diningName: string;
  entertainmentName: string;
  totalCost: number;
  status: string;
  notes: string;
}

export default function AdminDashboard() {
  const [authed, setAuthed] = useState(false);
  const [password, setPassword] = useState("");
  const [records, setRecords] = useState<ReceptionRecord[]>([]);
  const [filter, setFilter] = useState({ city: "", period: "month" });

  useEffect(() => {
    if (authed) loadRecords();
  }, [authed, filter]);

  const loadRecords = async () => {
    try {
      const res = await fetch("/api/admin/records?" + new URLSearchParams(filter));
      if (res.ok) {
        const data = await res.json();
        setRecords(data.records || []);
      }
    } catch {}
  };

  const handleLogin = () => {
    if (password === "chaxu2026") setAuthed(true);
  };

  if (!authed) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "#f8f9fa" }}>
        <div style={{ background: "white", padding: 40, borderRadius: 12, boxShadow: "0 2px 12px rgba(0,0,0,0.08)", width: 360 }}>
          <h2 style={{ marginBottom: 20, textAlign: "center" }}>差序管理后台</h2>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="请输入管理密码"
            style={{ width: "100%", padding: "10px 14px", border: "1px solid #dadce0", borderRadius: 8, marginBottom: 12, fontSize: 14 }}
          />
          <button onClick={handleLogin} style={{ width: "100%", padding: 10, background: "#1a73e8", color: "white", border: "none", borderRadius: 8, fontSize: 14, cursor: "pointer" }}>
            登录
          </button>
        </div>
      </div>
    );
  }

  const stats = {
    total: records.length,
    thisMonth: records.filter((r) => {
      const d = new Date(r.date);
      const now = new Date();
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }).length,
    totalCost: records.reduce((sum, r) => sum + (r.totalCost || 0), 0),
    vipCount: records.filter((r) => r.guestLevel === "VIP").length,
  };

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto", fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>差序管理后台</h1>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "总接待次数", value: stats.total },
          { label: "本月接待", value: stats.thisMonth },
          { label: "总消费(元)", value: "¥" + stats.totalCost.toLocaleString() },
          { label: "VIP接待", value: stats.vipCount },
        ].map((s, i) => (
          <div key={i} style={{ background: "white", padding: 20, borderRadius: 12, boxShadow: "0 1px 4px rgba(0,0,0,0.06)" }}>
            <div style={{ fontSize: 13, color: "#5f6368", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <select
          value={filter.city}
          onChange={(e) => setFilter({ ...filter, city: e.target.value })}
          style={{ padding: "8px 12px", border: "1px solid #dadce0", borderRadius: 8 }}
        >
          <option value="">全部城市</option>
          <option value="成都">成都</option>
          <option value="北京">北京</option>
          <option value="上海">上海</option>
          <option value="深圳">深圳</option>
          <option value="广州">广州</option>
        </select>
        <select
          value={filter.period}
          onChange={(e) => setFilter({ ...filter, period: e.target.value })}
          style={{ padding: "8px 12px", border: "1px solid #dadce0", borderRadius: 8 }}
        >
          <option value="week">本周</option>
          <option value="month">本月</option>
          <option value="quarter">本季度</option>
          <option value="year">全年</option>
        </select>
      </div>

      {/* Table */}
      <div style={{ background: "white", borderRadius: 12, boxShadow: "0 1px 4px rgba(0,0,0,0.06)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #f1f3f5" }}>
              {["日期", "城市", "客户", "级别", "餐厅", "娱乐", "消费", "状态"].map((h) => (
                <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontSize: 12, color: "#5f6368", fontWeight: 600 }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.length === 0 && (
              <tr>
                <td colSpan={8} style={{ padding: 40, textAlign: "center", color: "#9ca3af" }}>
                  暂无接待记录
                </td>
              </tr>
            )}
            {records.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid #f1f3f5" }}>
                <td style={{ padding: "12px 16px", fontSize: 13 }}>{r.date}</td>
                <td style={{ padding: "12px 16px", fontSize: 13 }}>{r.city}</td>
                <td style={{ padding: "12px 16px", fontSize: 13 }}>{r.guestName}</td>
                <td style={{ padding: "12px 16px" }}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 600,
                    background: r.guestLevel === "VIP" ? "#fee2e2" : "#dbeafe",
                    color: r.guestLevel === "VIP" ? "#991b1b" : "#1e40af",
                  }}>
                    {r.guestLevel}
                  </span>
                </td>
                <td style={{ padding: "12px 16px", fontSize: 13 }}>{r.diningName || "-"}</td>
                <td style={{ padding: "12px 16px", fontSize: 13 }}>{r.entertainmentName || "-"}</td>
                <td style={{ padding: "12px 16px", fontSize: 13 }}>¥{(r.totalCost || 0).toLocaleString()}</td>
                <td style={{ padding: "12px 16px" }}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    background: r.status === "completed" ? "#d1fae5" : "#fef3c7",
                    color: r.status === "completed" ? "#065f46" : "#92400e",
                  }}>
                    {r.status === "completed" ? "已完成" : "进行中"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
