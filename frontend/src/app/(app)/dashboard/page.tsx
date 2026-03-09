"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import StatsCard from "@/components/StatsCard";
import { OverviewAnalytics, Event } from "@/types";
import { CalendarDays, QrCode, ScanLine, Activity } from "lucide-react";
import Link from "next/link";
import { formatDate } from "@/lib/utils";

export default function DashboardPage() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<OverviewAnalytics | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/api/analytics/overview"),
      api.get("/api/events"),
    ]).then(([ov, ev]) => {
      setOverview(ov.data);
      setEvents(ev.data.slice(0, 5));
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Welcome back, {user?.username} 👋
        </h1>
        <p className="text-slate-500 mt-1 text-sm">Here&apos;s a snapshot of your QR platform.</p>
      </div>

      {/* Stats */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse h-24 bg-slate-100" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatsCard label="Total Events" value={overview?.total_events ?? 0} icon={CalendarDays} color="blue" />
          <StatsCard label="QR Codes" value={overview?.total_qr_codes ?? 0} icon={QrCode} color="emerald" />
          <StatsCard label="Scans (30d)" value={overview?.total_scans_30d ?? 0} icon={ScanLine} color="violet" />
          <StatsCard label="Total Scans" value={overview?.total_scans_all ?? 0} icon={Activity} color="amber" />
        </div>
      )}

      {/* Recent events */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800">Recent Events</h2>
          <Link href="/events" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
            View all →
          </Link>
        </div>
        {events.length === 0 && !loading ? (
          <div className="px-6 py-12 text-center">
            <CalendarDays className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No events yet.</p>
            <Link href="/events" className="btn-primary mt-4 inline-flex">Create your first event</Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {events.map((ev) => (
              <Link
                key={ev.id}
                href={`/events/${ev.id}`}
                className="flex items-center justify-between px-6 py-3.5 hover:bg-slate-50 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                    <CalendarDays className="w-4 h-4 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-800 group-hover:text-blue-600 transition-colors">
                      {ev.name}
                    </p>
                    <p className="text-xs text-slate-400">{formatDate(ev.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span>{ev.qr_count} QRs</span>
                  <span className="font-medium text-slate-700">{ev.total_scans} scans</span>
                  <span className={ev.is_active ? "badge-green" : "badge-red"}>
                    {ev.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
