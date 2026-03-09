"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import toast from "react-hot-toast";
import { EventAnalytics } from "@/types";
import { ArrowLeft, Activity, QrCode, Smartphone, Monitor, Tablet } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell, Legend,
} from "recharts";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

const deviceIcon = (type: string) => {
  if (type === "mobile") return <Smartphone className="w-4 h-4" />;
  if (type === "desktop") return <Monitor className="w-4 h-4" />;
  if (type === "tablet") return <Tablet className="w-4 h-4" />;
  return <Activity className="w-4 h-4" />;
};

export default function AnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<EventAnalytics | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/analytics/events/${id}?days=${days}`);
      setData(res.data);
    } catch {
      toast.error("Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAnalytics(); }, [id, days]);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Link href={`/events/${id}`} className="text-slate-400 hover:text-slate-700 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {data ? `Analytics: ${data.event_name}` : "Analytics"}
            </h1>
            <p className="text-slate-500 text-sm mt-0.5">Scan performance and engagement breakdown.</p>
          </div>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="input w-36 text-sm"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last 365 days</option>
        </select>
      </div>

      {loading || !data ? (
        <div className="flex items-center justify-center py-32">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Total scans hero */}
          <div className="card p-6 flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center">
              <Activity className="w-7 h-7 text-white" />
            </div>
            <div>
              <p className="text-slate-500 text-sm font-medium">Total Scans ({days}d)</p>
              <p className="text-4xl font-bold text-slate-900 mt-0.5">{data.total_scans.toLocaleString()}</p>
            </div>
          </div>

          {/* Time series */}
          <div className="card p-6">
            <h2 className="font-semibold text-slate-800 mb-5">Scan Timeline</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.time_series} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  tickFormatter={(v) => {
                    const d = new Date(v);
                    return `${d.getMonth() + 1}/${d.getDate()}`;
                  }}
                />
                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ borderRadius: "10px", border: "1px solid #e2e8f0", fontSize: 12 }}
                  labelFormatter={(l) => `Date: ${l}`}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  name="Scans"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* QR breakdown */}
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="card p-6">
              <h2 className="font-semibold text-slate-800 mb-5">QR Code Comparison</h2>
              {data.qr_breakdown.length === 0 ? (
                <p className="text-slate-400 text-sm">No QR codes yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={data.qr_breakdown} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: "10px", border: "1px solid #e2e8f0", fontSize: 12 }}
                    />
                    <Bar dataKey="scan_count" name="Scans" radius={[4, 4, 0, 0]}>
                      {data.qr_breakdown.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Device breakdown */}
            <div className="card p-6">
              <h2 className="font-semibold text-slate-800 mb-5">Device Breakdown</h2>
              {data.device_breakdown.length === 0 ? (
                <p className="text-slate-400 text-sm">No scan data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={data.device_breakdown}
                      dataKey="count"
                      nameKey="device_type"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      innerRadius={40}
                      paddingAngle={3}
                    >
                      {data.device_breakdown.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Legend
                      formatter={(value) => <span className="text-xs text-slate-600 capitalize">{value}</span>}
                    />
                    <Tooltip
                      contentStyle={{ borderRadius: "10px", border: "1px solid #e2e8f0", fontSize: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* QR code table */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">QR Code Details</h2>
            </div>
            <div className="divide-y divide-slate-100">
              {data.qr_breakdown.map((qr, i) => (
                <div key={qr.qr_id} className="flex items-center gap-4 px-6 py-3.5">
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ background: COLORS[i % COLORS.length] }}
                  />
                  <div className="flex-1">
                    <span className="text-sm font-medium text-slate-800">{qr.label}</span>
                    <span className="text-xs text-slate-400 ml-2 font-mono">{qr.short_id}</span>
                  </div>
                  <span className={qr.is_active ? "badge-green" : "badge-red"}>
                    {qr.is_active ? "Active" : "Inactive"}
                  </span>
                  <span className="text-sm font-bold text-slate-800 w-16 text-right">
                    {qr.scan_count.toLocaleString()}
                  </span>
                  <span className="text-xs text-slate-400 w-12 text-right">scans</span>
                </div>
              ))}
            </div>
          </div>

          {/* Top browsers */}
          {data.top_browsers.length > 0 && (
            <div className="card p-6">
              <h2 className="font-semibold text-slate-800 mb-5">Top Browsers</h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={data.top_browsers.slice(0, 8)}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "#94a3b8" }} allowDecimals={false} />
                  <YAxis type="category" dataKey="browser" tick={{ fontSize: 11, fill: "#94a3b8" }} width={80} />
                  <Tooltip
                    contentStyle={{ borderRadius: "10px", border: "1px solid #e2e8f0", fontSize: 12 }}
                  />
                  <Bar dataKey="count" name="Scans" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
