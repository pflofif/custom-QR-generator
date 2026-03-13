"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import Modal from "@/components/Modal";
import api from "@/lib/api";
import toast from "react-hot-toast";
import { QRCode } from "@/types";
import { Upload, X, Sparkles, Trash2, RefreshCw, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  qr: QRCode | null;
  eventId: string;
  onClose: () => void;
  onSaved: () => void;
}

const DEBOUNCE_MS = 700;

/** Inline hover tooltip — no extra libraries needed */
function InfoTip({ text }: { text: string }) {
  return (
    <span className="relative group inline-flex items-center ml-1 align-middle">
      <HelpCircle className="w-3.5 h-3.5 text-slate-400 cursor-help" />
      <span className={cn(
        "absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-60 rounded-lg",
        "bg-slate-800 text-white text-xs px-3 py-2 shadow-xl leading-relaxed text-left",
        "opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50",
      )}>
        {text}
        {/* arrow */}
        <span className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-slate-800" />
      </span>
    </span>
  );
}

export default function CustomizeQRModal({ qr, eventId, onClose, onSaved }: Props) {
  const [colorized, setColorized] = useState(false);
  const [contrast, setContrast] = useState(1.0);
  const [brightness, setBrightness] = useState(1.0);
  const [version, setVersion] = useState(1);
  const [level, setLevel] = useState<"L" | "M" | "Q" | "H">("H");

  const [bgFile, setBgFile] = useState<File | null>(null);
  const [bgPreview, setBgPreview] = useState<string | null>(null);
  const [hasStoredBg, setHasStoredBg] = useState(false);
  const [ignoreStoredBg, setIgnoreStoredBg] = useState(false);

  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevPreviewRef = useRef<string | null>(null);

  // Initialise controls from saved style when QR changes
  useEffect(() => {
    if (!qr) return;
    const s = qr.custom_style;
    setColorized(s?.colorized ?? false);
    setContrast(s?.contrast ?? 1.0);
    setBrightness(s?.brightness ?? 1.0);
    setVersion(s?.version ?? 1);
    setLevel((s?.level as "L" | "M" | "Q" | "H") ?? "H");
    setHasStoredBg(s?.has_background ?? false);
    setIgnoreStoredBg(false);
    setBgFile(null);
    setBgPreview(null);
  }, [qr]);

  // Revoke object URLs on unmount
  useEffect(() => {
    return () => {
      if (bgPreview) URL.revokeObjectURL(bgPreview);
      if (prevPreviewRef.current) URL.revokeObjectURL(prevPreviewRef.current);
    };
  }, []);

  const triggerPreview = useCallback(() => {
    if (!qr) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setPreviewLoading(true);
      try {
        const fd = new FormData();
        fd.append("colorized", String(colorized));
        fd.append("contrast", String(contrast));
        fd.append("brightness", String(brightness));
        fd.append("version", String(version));
        fd.append("level", level);
        fd.append("ignore_stored_bg", String(ignoreStoredBg));
        if (bgFile) fd.append("background", bgFile);

        const res = await api.post(
          `/api/events/${eventId}/qrcodes/${qr.id}/preview`,
          fd,
          { responseType: "blob" },
        );
        const url = URL.createObjectURL(res.data);
        setPreviewSrc((old) => {
          if (old) URL.revokeObjectURL(old);
          prevPreviewRef.current = url;
          return url;
        });
      } catch {
        // silent — preview errors don't need a toast
      } finally {
        setPreviewLoading(false);
      }
    }, DEBOUNCE_MS);
  }, [qr, eventId, colorized, contrast, brightness, version, level, bgFile, ignoreStoredBg]);

  useEffect(() => {
    triggerPreview();
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [triggerPreview]);

  const handleBgSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!["jpg", "jpeg", "png", "gif"].includes(ext)) {
      toast.error("Only JPG, PNG or GIF files are supported");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error("File must be under 2 MB");
      return;
    }
    if (bgPreview) URL.revokeObjectURL(bgPreview);
    setBgFile(file);
    setBgPreview(URL.createObjectURL(file));
    setIgnoreStoredBg(false);
  };

  const removeBgFile = () => {
    if (bgPreview) { URL.revokeObjectURL(bgPreview); setBgPreview(null); }
    setBgFile(null);
  };

  const removeStoredBg = () => {
    setHasStoredBg(false);
    setIgnoreStoredBg(true);
  };

  const handleSave = async () => {
    if (!qr) return;
    setSaving(true);
    try {
      await api.post(`/api/events/${eventId}/qrcodes/${qr.id}/style`, {
        colorized, contrast, brightness, version, level,
      });
      if (bgFile) {
        const fd = new FormData();
        fd.append("background", bgFile);
        await api.post(`/api/events/${eventId}/qrcodes/${qr.id}/background`, fd);
      } else if (ignoreStoredBg && qr.custom_style?.has_background) {
        await api.delete(`/api/events/${eventId}/qrcodes/${qr.id}/background`);
      }
      toast.success("Custom style saved!");
      onSaved();
      onClose();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to save style");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!qr) return;
    if (!confirm("Remove all custom styling and revert to the default QR code?")) return;
    setSaving(true);
    try {
      await api.delete(`/api/events/${eventId}/qrcodes/${qr.id}/style`);
      toast.success("Style reset to default");
      onSaved();
      onClose();
    } catch {
      toast.error("Failed to reset style");
    } finally {
      setSaving(false);
    }
  };

  const showsBg = bgFile !== null || (hasStoredBg && !ignoreStoredBg);

  if (!qr) return null;

  return (
    <Modal open={!!qr} onClose={onClose} title={`✨ Customize: ${qr.label}`} size="lg">
      <div className="flex gap-6">
        {/* ── Left: controls ─────────────────────────────────────────────── */}
        <div className="flex-1 space-y-5">

          {/* Background image */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Background image
              <InfoTip text="Upload an image (JPG/PNG) or animated GIF to blend with the QR code pattern. Square images look best. Use a GIF to get an animated QR code output." />
              <span className="ml-2 text-slate-400 font-normal text-xs">(JPG / PNG / GIF · max 2 MB)</span>
            </label>

            {!showsBg && (
              <label className={cn(
                "flex flex-col items-center justify-center gap-2 border-2 border-dashed",
                "border-slate-200 rounded-xl p-6 cursor-pointer transition-colors text-center",
                "hover:border-blue-400 hover:bg-blue-50/40",
              )}>
                <Upload className="w-6 h-6 text-slate-400" />
                <span className="text-sm text-slate-500">Click to upload or drag & drop</span>
                <span className="text-xs text-slate-400">Square images look best · GIF for animated QR</span>
                <input type="file" accept=".jpg,.jpeg,.png,.gif" className="hidden" onChange={handleBgSelect} />
              </label>
            )}

            {showsBg && (
              <div className="flex items-center gap-3 bg-slate-50 rounded-xl p-3 border border-slate-200">
                {bgPreview ? (
                  <img src={bgPreview} alt="bg" className="w-14 h-14 object-cover rounded-lg shrink-0" />
                ) : (
                  <div className="w-14 h-14 bg-slate-200 rounded-lg shrink-0 flex items-center justify-center text-xs text-slate-400">
                    Stored
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-700 truncate">
                    {bgFile ? bgFile.name : "Saved background"}
                  </p>
                  <p className="text-xs text-slate-400">
                    {bgFile ? `${(bgFile.size / 1024).toFixed(0)} KB` : "Stored in MinIO"}
                  </p>
                </div>
                <button
                  onClick={bgFile ? removeBgFile : removeStoredBg}
                  className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                  title="Remove background"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Colorized toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-700 inline-flex items-center">
                Colorized
                <InfoTip text="When enabled, the background image keeps its original colors in the QR output. When disabled, the image is converted to black & white first. Only applies when a background image is set." />
              </p>
              <p className="text-xs text-slate-400 mt-0.5">Keep the background image colors in the QR</p>
            </div>
            <button
              type="button"
              onClick={() => setColorized(!colorized)}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                colorized ? "bg-blue-600" : "bg-slate-200",
              )}
            >
              <span className={cn(
                "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform",
                colorized ? "translate-x-6" : "translate-x-1",
              )} />
            </button>
          </div>

          {/* Contrast */}
          <div>
            <div className="flex justify-between mb-1">
              <label className="text-sm font-medium text-slate-700 inline-flex items-center">
                Contrast
                <InfoTip text="Adjusts the contrast of the background image before blending. Values above 1.0 increase contrast (sharper dark/light separation), values below 1.0 reduce it. Default is 1.0 (unchanged)." />
              </label>
              <span className="text-sm tabular-nums text-slate-500">{contrast.toFixed(1)}</span>
            </div>
            <input
              type="range" min="0.5" max="2.5" step="0.1"
              value={contrast} onChange={(e) => setContrast(parseFloat(e.target.value))}
              className="w-full accent-blue-600"
            />
          </div>

          {/* Brightness */}
          <div>
            <div className="flex justify-between mb-1">
              <label className="text-sm font-medium text-slate-700 inline-flex items-center">
                Brightness
                <InfoTip text="Adjusts the brightness of the background image. Values above 1.0 make it lighter, values below 1.0 make it darker. Higher brightness can improve QR scanability. Default is 1.0 (unchanged)." />
              </label>
              <span className="text-sm tabular-nums text-slate-500">{brightness.toFixed(1)}</span>
            </div>
            <input
              type="range" min="0.5" max="2.5" step="0.1"
              value={brightness} onChange={(e) => setBrightness(parseFloat(e.target.value))}
              className="w-full accent-blue-600"
            />
          </div>

          {/* Version + Level */}
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-700 mb-1 inline-flex items-center">
                Version
                <InfoTip text="Controls the size (module count) of the QR code grid. Version 1 = 21×21 modules, Version 40 = 177×177 modules. Use a higher version when your background image is large, so the QR pattern stays readable. Default 1 is fine for most URLs." />
                <span className="ml-1 text-slate-400 font-normal text-xs">(1–40)</span>
              </label>
              <input
                type="number" min={1} max={40} className="input"
                value={version}
                onChange={(e) => setVersion(Math.max(1, Math.min(40, parseInt(e.target.value) || 1)))}
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-700 mb-1 inline-flex items-center">
                Error correction
                <InfoTip text="How much of the QR code can be damaged or covered and still scan correctly. L=7%, M=15%, Q=25%, H=30%. Use H (default) when overlaying a background image — the pattern needs more redundancy to remain scannable." />
              </label>
              <select
                className="input"
                value={level}
                onChange={(e) => setLevel(e.target.value as "L" | "M" | "Q" | "H")}
              >
                <option value="L">L — Low (7%)</option>
                <option value="M">M — Medium (15%)</option>
                <option value="Q">Q — Quartile (25%)</option>
                <option value="H">H — High (30%)</option>
              </select>
            </div>
          </div>
        </div>

        {/* ── Right: live preview ──────────────────────────────────────────── */}
        <div className="w-48 shrink-0 flex flex-col items-center gap-3">
          <p className="text-sm font-medium text-slate-700 self-start">Live preview</p>
          <div className={cn(
            "w-44 h-44 rounded-xl border-2 border-slate-200 flex items-center justify-center",
            "bg-slate-50 overflow-hidden transition-opacity",
            previewLoading && "opacity-50",
          )}>
            {previewLoading && !previewSrc && (
              <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
            )}
            {previewSrc && (
              <img src={previewSrc} alt="QR preview" className="w-full h-full object-contain" />
            )}
            {!previewLoading && !previewSrc && (
              <span className="text-xs text-slate-400 text-center px-3">
                Adjust settings to preview
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 text-center">Updates automatically</p>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-6 pt-5 border-t border-slate-100">
        <button
          onClick={handleReset}
          disabled={saving || !qr.custom_style}
          className="btn-secondary text-red-600 border-red-200 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5" /> Reset to default
        </button>
        <div className="flex gap-2">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            <Sparkles className="w-3.5 h-3.5" />
            {saving ? "Rendering & saving…" : "Save style"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
