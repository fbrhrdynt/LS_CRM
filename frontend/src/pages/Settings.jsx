import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, Upload, Save, Package, BookOpen } from "lucide-react";
import api, { API, formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function Settings() {
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [includeBuild, setIncludeBuild] = useState(false);

  const downloadInstallGuide = async () => {
    try {
      const res = await api.get("/settings/installation-guide/pdf", { responseType: "blob" });
      const u = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = u;
      a.download = "LogiSource-Installation-Guide.pdf";
      a.click();
      window.URL.revokeObjectURL(u);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);

  if (!s) return <div className="text-sm text-muted-foreground">Loading…</div>;

  const setF = (k, v) => setS((cur) => ({ ...cur, [k]: v }));

  const save = async () => {
    setBusy(true);
    try {
      const payload = { ...s, tax_percent: Number(s.tax_percent || 0) };
      await api.put("/settings", payload);
      toast.success("Settings saved");
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const backup = async () => {
    try {
      const res = await api.get("/settings/backup", { responseType: "blob" });
      const u = window.URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = u; a.download = `logisource-backup-${Date.now()}.json`; a.click();
      window.URL.revokeObjectURL(u);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const restore = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!confirm("Restore will REPLACE all data except users. Continue?")) { e.target.value = ""; return; }
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await fetch(`${API}/settings/restore`, {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Restore failed");
      toast.success(`Restored ${Object.keys(data.restored).length} collections`);
    } catch (err) { toast.error(err.message); }
    finally { e.target.value = ""; }
  };

  const fullExport = async () => {
    setExporting(true);
    toast.info(
      includeBuild
        ? "Building frontend + bundling database… this can take up to 3 minutes."
        : "Bundling source + database… this can take up to 60 seconds."
    );
    try {
      const res = await api.get("/settings/full-export", {
        params: { include_build: includeBuild ? "true" : "false" },
        responseType: "blob",
        timeout: 300000,
      });
      const size = Number(res.headers["x-export-size-kb"] || 0);
      const withBuild = res.headers["x-include-build"] === "1";
      const buildWarn = res.headers["x-build-warning"];
      const u = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 15);
      a.href = u; a.download = `logisource-full-${ts}.zip`; a.click();
      window.URL.revokeObjectURL(u);
      if (buildWarn) toast.warning(`Downloaded but build skipped: ${buildWarn}`);
      else toast.success(`Download started · ${size} KB${withBuild ? " · includes production build" : ""}`);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setExporting(false); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Admin"
        title="Website Settings"
        description="Company profile, invoicing defaults, and database backup / restore."
        actions={<Button size="sm" onClick={save} disabled={busy} data-testid="settings-save-button"><Save className="h-4 w-4 mr-2" strokeWidth={1.5} />{busy ? "Saving..." : "Save"}</Button>}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="border border-border bg-card">
          <div className="px-5 py-3 border-b border-border font-display font-medium">Company Profile</div>
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-3">
            <F label="Company Name"><Input value={s.company_name || ""} onChange={(e) => setF("company_name", e.target.value)} /></F>
            <F label="Tagline"><Input value={s.company_tagline || ""} onChange={(e) => setF("company_tagline", e.target.value)} /></F>
            <F label="Email"><Input value={s.company_email || ""} onChange={(e) => setF("company_email", e.target.value)} /></F>
            <F label="Phone"><Input value={s.company_phone || ""} onChange={(e) => setF("company_phone", e.target.value)} /></F>
            <F label="Logo URL" span={2}><Input value={s.company_logo_url || ""} onChange={(e) => setF("company_logo_url", e.target.value)} /></F>
            <F label="Address" span={2}><Textarea rows={2} value={s.company_address || ""} onChange={(e) => setF("company_address", e.target.value)} /></F>
          </div>
        </section>

        <section className="border border-border bg-card">
          <div className="px-5 py-3 border-b border-border font-display font-medium">Documents & Numbering</div>
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-3">
            <F label="Currency"><Input value={s.currency || ""} onChange={(e) => setF("currency", e.target.value)} /></F>
            <F label="Default Tax %"><Input type="number" step="0.01" value={s.tax_percent || 0} onChange={(e) => setF("tax_percent", e.target.value)} /></F>
            <F label="Quotation Prefix"><Input value={s.quotation_prefix || ""} onChange={(e) => setF("quotation_prefix", e.target.value)} /></F>
            <F label="Invoice Prefix"><Input value={s.invoice_prefix || ""} onChange={(e) => setF("invoice_prefix", e.target.value)} /></F>
            <F label="Project Prefix" span={2}><Input value={s.project_prefix || ""} onChange={(e) => setF("project_prefix", e.target.value)} /></F>
          </div>
        </section>

        <section className="border border-border bg-card lg:col-span-2">
          <div className="px-5 py-3 border-b border-border font-display font-medium">Backup & Restore</div>
          <div className="p-5 flex flex-col md:flex-row md:items-center gap-4">
            <div className="flex-1">
              <div className="font-medium mb-1">Download database backup</div>
              <div className="text-sm text-muted-foreground">Exports every collection as a single JSON file. Store securely — the file contains encrypted vault entries.</div>
            </div>
            <Button variant="outline" onClick={backup} data-testid="settings-backup-button"><Download className="h-4 w-4 mr-2" strokeWidth={1.5} />Backup</Button>
          </div>
          <div className="border-t border-border p-5 flex flex-col md:flex-row md:items-center gap-4">
            <div className="flex-1">
              <div className="font-medium mb-1">Restore from backup</div>
              <div className="text-sm text-destructive">Warning: replaces ALL data except users.</div>
            </div>
            <label className="cursor-pointer">
              <input type="file" accept=".json" className="hidden" onChange={restore} data-testid="settings-restore-input" />
              <Button variant="outline" asChild><span><Upload className="h-4 w-4 mr-2" strokeWidth={1.5} />Restore</span></Button>
            </label>
          </div>
          <div className="border-t border-border p-5 flex flex-col md:flex-row md:items-center gap-4">
            <div className="flex-1">
              <div className="font-medium mb-1">Installation &amp; Deployment Guide (PDF)</div>
              <div className="text-sm text-muted-foreground">
                Step-by-step tutorial to install LogiSource on your local PC (Windows / macOS / Linux),
                or deploy to a production VPS with nginx + HTTPS. Also includes Docker &amp; Netlify examples.
              </div>
            </div>
            <Button variant="outline" onClick={downloadInstallGuide} data-testid="settings-install-guide-button">
              <BookOpen className="h-4 w-4 mr-2" strokeWidth={1.5} /> Installation Guide (PDF)
            </Button>
          </div>
          <div className="border-t border-border p-5 flex flex-col md:flex-row md:items-center gap-4">
            <div className="flex-1">
              <div className="font-medium mb-1">Download full source + database (ZIP)</div>
              <div className="text-sm text-muted-foreground">
                Bundles backend, frontend (no <code>node_modules</code>), MongoDB dump, and non-secret project files.
                Secret <code>backend/.env</code> and credential files are intentionally excluded.
              </div>
              <label className="mt-3 flex items-center gap-2 text-sm cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={includeBuild}
                  onChange={(e) => setIncludeBuild(e.target.checked)}
                  className="h-4 w-4 accent-primary"
                  data-testid="settings-include-build-checkbox"
                />
                <span>Also compile & include <code>frontend/build/</code> (adds ~60–120s, ready for Netlify / S3 / nginx)</span>
              </label>
            </div>
            <Button variant="outline" onClick={fullExport} disabled={exporting} data-testid="settings-full-export-button">
              <Package className="h-4 w-4 mr-2" strokeWidth={1.5} />
              {exporting ? (includeBuild ? "Building…" : "Bundling…") : "Download ZIP"}
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}

function F({ label, span = 1, children }) {
  return (
    <div className={`space-y-1.5 ${span === 2 ? "md:col-span-2" : ""}`}>
      <Label className="text-xs uppercase tracking-widest">{label}</Label>
      {children}
    </div>
  );
}
