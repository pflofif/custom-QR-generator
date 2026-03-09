"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import toast from "react-hot-toast";
import Modal from "@/components/Modal";
import { Event, EventCreatePayload } from "@/types";
import { CalendarDays, Plus, Trash2, BarChart3, ArrowRight } from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<EventCreatePayload>({ name: "", description: "" });
  const [saving, setSaving] = useState(false);

  const fetchEvents = async () => {
    try {
      const { data } = await api.get("/api/events");
      setEvents(data);
    } catch {
      toast.error("Failed to load events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchEvents(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/api/events", form);
      toast.success("Event created!");
      setCreateOpen(false);
      setForm({ name: "", description: "" });
      fetchEvents();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to create event");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (ev: Event) => {
    if (!confirm(`Delete event "${ev.name}"? All QR codes and scan data will be lost.`)) return;
    try {
      await api.delete(`/api/events/${ev.id}`);
      toast.success("Event deleted");
      setEvents((prev) => prev.filter((e) => e.id !== ev.id));
    } catch {
      toast.error("Failed to delete event");
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Events</h1>
          <p className="text-slate-500 text-sm mt-1">Manage your QR code campaigns.</p>
        </div>
        <button onClick={() => setCreateOpen(true)} className="btn-primary">
          <Plus className="w-4 h-4" /> New Event
        </button>
      </div>

      {loading ? (
        <div className="grid gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card h-24 animate-pulse bg-slate-100" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="card py-16 text-center">
          <CalendarDays className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 font-medium mb-1">No events yet</p>
          <p className="text-slate-400 text-sm mb-4">Create your first event to start generating dynamic QR codes.</p>
          <button onClick={() => setCreateOpen(true)} className="btn-primary mx-auto">
            <Plus className="w-4 h-4" /> Create Event
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {events.map((ev) => (
            <div key={ev.id} className="card p-5 flex items-center justify-between gap-4 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center shrink-0">
                  <CalendarDays className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-slate-800 truncate">{ev.name}</h3>
                    <span className={ev.is_active ? "badge-green" : "badge-red"}>
                      {ev.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  {ev.description && (
                    <p className="text-xs text-slate-400 truncate">{ev.description}</p>
                  )}
                  <p className="text-xs text-slate-400 mt-0.5">
                    Created {formatDate(ev.created_at)} · {ev.qr_count} QR codes · {ev.total_scans} total scans
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Link href={`/events/${ev.id}/analytics`} className="btn-secondary text-xs py-1.5">
                  <BarChart3 className="w-3.5 h-3.5" /> Analytics
                </Link>
                <Link href={`/events/${ev.id}`} className="btn-primary text-xs py-1.5">
                  Manage <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <button
                  onClick={() => handleDelete(ev)}
                  className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Create New Event">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Event name *</label>
            <input
              required
              className="input"
              placeholder="e.g. Hackathon 2025"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              rows={3}
              className="input resize-none"
              placeholder="Optional description…"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setCreateOpen(false)} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Creating…" : "Create Event"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
