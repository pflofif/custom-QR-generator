"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import toast from "react-hot-toast";
import Modal from "@/components/Modal";
import CustomizeQRModal from "@/components/CustomizeQRModal";
import { Event, QRCode, QRCreatePayload, QRUpdatePayload } from "@/types";
import {
  ArrowLeft, BarChart3, Plus, QrCode, Pencil, Trash2,
  ToggleLeft, ToggleRight, Copy, ExternalLink, Download, Sparkles,
} from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<Event | null>(null);
  const [qrs, setQrs] = useState<QRCode[]>([]);
  const [loading, setLoading] = useState(true);

  // modals
  const [createOpen, setCreateOpen] = useState(false);
  const [editQR, setEditQR] = useState<QRCode | null>(null);
  const [editEvent, setEditEvent] = useState(false);
  const [qrImageModal, setQrImageModal] = useState<QRCode | null>(null);
  const [customizeQR, setCustomizeQR] = useState<QRCode | null>(null);

  // forms
  const [createForm, setCreateForm] = useState<QRCreatePayload>({ label: "", target_url: "" });
  const [editForm, setEditForm] = useState<QRUpdatePayload>({});
  const [eventForm, setEventForm] = useState({ name: "", description: "" });
  const [saving, setSaving] = useState(false);

  const fetchData = async () => {
    try {
      const [evRes, qrRes] = await Promise.all([
        api.get(`/api/events/${id}`),
        api.get(`/api/events/${id}/qrcodes`),
      ]);
      setEvent(evRes.data);
      setQrs(qrRes.data);
      setEventForm({ name: evRes.data.name, description: evRes.data.description || "" });
    } catch {
      toast.error("Failed to load event");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleCreateQR = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post(`/api/events/${id}/qrcodes`, createForm);
      toast.success("QR code created!");
      setCreateOpen(false);
      setCreateForm({ label: "", target_url: "" });
      fetchData();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to create QR code");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateQR = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editQR) return;
    setSaving(true);
    try {
      await api.put(`/api/events/${id}/qrcodes/${editQR.id}`, editForm);
      toast.success("QR code updated!");
      setEditQR(null);
      fetchData();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to update");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteQR = async (qr: QRCode) => {
    if (!confirm(`Delete QR code "${qr.label}"?`)) return;
    try {
      await api.delete(`/api/events/${id}/qrcodes/${qr.id}`);
      toast.success("QR code deleted");
      setQrs((prev) => prev.filter((q) => q.id !== qr.id));
    } catch {
      toast.error("Failed to delete QR code");
    }
  };

  const handleToggleActive = async (qr: QRCode) => {
    try {
      await api.put(`/api/events/${id}/qrcodes/${qr.id}`, { is_active: !qr.is_active });
      toast.success(qr.is_active ? "QR code deactivated" : "QR code activated");
      fetchData();
    } catch {
      toast.error("Failed to toggle status");
    }
  };

  const handleSaveEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put(`/api/events/${id}`, eventForm);
      toast.success("Event updated!");
      setEditEvent(false);
      fetchData();
    } catch {
      toast.error("Failed to update event");
    } finally {
      setSaving(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  };

  const downloadQR = async (qr: QRCode) => {
    try {
      const res = await api.get(`/api/events/${id}/qrcodes/${qr.id}/image`, { responseType: "blob" });
      const contentType: string = res.headers["content-type"] ?? "";
      const ext = contentType.includes("gif") ? "gif" : "png";
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${qr.label.replace(/\s+/g, "_")}_qr.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download QR image");
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!event) return <div className="p-8 text-slate-500">Event not found.</div>;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Back + Header */}
      <div className="flex items-start justify-between mb-8 gap-4">
        <div className="flex items-start gap-3">
          <Link href="/events" className="mt-1 text-slate-400 hover:text-slate-700 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900">{event.name}</h1>
              <span className={event.is_active ? "badge-green" : "badge-red"}>
                {event.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            {event.description && (
              <p className="text-slate-500 text-sm mt-0.5">{event.description}</p>
            )}
            <p className="text-xs text-slate-400 mt-1">
              {event.qr_count} QR codes · {event.total_scans} total scans · Created {formatDate(event.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button onClick={() => setEditEvent(true)} className="btn-secondary text-xs py-1.5">
            <Pencil className="w-3.5 h-3.5" /> Edit
          </button>
          <Link href={`/events/${id}/analytics`} className="btn-secondary text-xs py-1.5">
            <BarChart3 className="w-3.5 h-3.5" /> Analytics
          </Link>
          <button onClick={() => setCreateOpen(true)} className="btn-primary text-xs py-1.5">
            <Plus className="w-3.5 h-3.5" /> Add QR Code
          </button>
        </div>
      </div>

      {/* QR Codes */}
      {qrs.length === 0 ? (
        <div className="card py-16 text-center">
          <QrCode className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 font-medium mb-1">No QR codes yet</p>
          <p className="text-slate-400 text-sm mb-4">
            Create QR codes for this event (e.g. "Entrance Poster", "Table Sticker").
          </p>
          <button onClick={() => setCreateOpen(true)} className="btn-primary mx-auto">
            <Plus className="w-4 h-4" /> Add QR Code
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {qrs.map((qr) => (
            <div key={qr.id} className={cn("card p-5 transition-all", !qr.is_active && "opacity-60")}>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center shrink-0 mt-0.5">
                  <QrCode className="w-5 h-5 text-slate-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-slate-800">{qr.label}</span>
                    <span className={qr.is_active ? "badge-green" : "badge-red"}>
                      {qr.is_active ? "Active" : "Inactive"}
                    </span>
                    <span className="badge-blue">{qr.scan_count} scans</span>
                    {qr.custom_style && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-violet-100 text-violet-700">
                        <Sparkles className="w-3 h-3" /> Custom
                      </span>
                    )}
                  </div>

                  {/* Destination URL */}
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-xs text-slate-400 shrink-0">Destination:</span>
                    <a
                      href={qr.target_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline truncate max-w-xs"
                    >
                      {qr.target_url}
                    </a>
                    <ExternalLink className="w-3 h-3 text-slate-400 shrink-0" />
                  </div>

                  {/* Proxy URL */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-slate-400 shrink-0">Proxy URL:</span>
                    <span className="text-xs font-mono text-slate-600 truncate max-w-xs">{qr.proxy_url}</span>
                    <button
                      onClick={() => copyToClipboard(qr.proxy_url)}
                      className="text-slate-400 hover:text-blue-600 transition-colors"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => downloadQR(qr)}
                    className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                    title="Download QR Image"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setCustomizeQR(qr)}
                    className="w-8 h-8 flex items-center justify-center rounded-lg transition-colors"
                    title="Customize QR style"
                    style={{ color: qr.custom_style ? "#7c3aed" : undefined }}
                  >
                    <Sparkles className={`w-4 h-4 ${qr.custom_style ? "text-violet-500" : "text-slate-400 hover:text-violet-500"}`} />
                  </button>
                  <button
                    onClick={() => { setEditQR(qr); setEditForm({ label: qr.label, target_url: qr.target_url }); }}
                    className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                    title="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleToggleActive(qr)}
                    className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-amber-600 hover:bg-amber-50 transition-colors"
                    title={qr.is_active ? "Deactivate" : "Activate"}
                  >
                    {qr.is_active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => handleDeleteQR(qr)}
                    className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create QR Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add QR Code">
        <form onSubmit={handleCreateQR} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Label *</label>
            <input
              required
              className="input"
              placeholder="e.g. Entrance Poster"
              value={createForm.label}
              onChange={(e) => setCreateForm((f) => ({ ...f, label: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Destination URL *</label>
            <input
              required
              type="url"
              className="input"
              placeholder="https://example.com/register"
              value={createForm.target_url}
              onChange={(e) => setCreateForm((f) => ({ ...f, target_url: e.target.value }))}
            />
            <p className="text-xs text-slate-400 mt-1">This is where users will be redirected when they scan the QR.</p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setCreateOpen(false)} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Creating…" : "Create QR Code"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit QR Modal */}
      <Modal open={!!editQR} onClose={() => setEditQR(null)} title="Edit QR Code">
        <form onSubmit={handleUpdateQR} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Label</label>
            <input
              className="input"
              value={editForm.label || ""}
              onChange={(e) => setEditForm((f) => ({ ...f, label: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Destination URL</label>
            <input
              type="url"
              className="input"
              value={editForm.target_url || ""}
              onChange={(e) => setEditForm((f) => ({ ...f, target_url: e.target.value }))}
            />
            <p className="text-xs text-slate-400 mt-1">
              Changing this URL updates all existing printed QR codes instantly.
            </p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setEditQR(null)} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Customize QR Modal */}
      <CustomizeQRModal
        qr={customizeQR}
        eventId={id}
        onClose={() => setCustomizeQR(null)}
        onSaved={fetchData}
      />

      {/* Edit Event Modal */}
      <Modal open={editEvent} onClose={() => setEditEvent(false)} title="Edit Event">
        <form onSubmit={handleSaveEvent} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Event name</label>
            <input
              required
              className="input"
              value={eventForm.name}
              onChange={(e) => setEventForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              rows={3}
              className="input resize-none"
              value={eventForm.description}
              onChange={(e) => setEventForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setEditEvent(false)} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
