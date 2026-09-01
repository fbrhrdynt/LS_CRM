import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Copy, Zap, Ban, Check, Trash2, RefreshCw, BookOpen } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { fmtDate, fmtDateTime, fmtRelative } from "@/lib/format";

const STATUS_TONE = {
  active: "bg-success/15 text-success border-success/40",
  suspended: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  revoked: "bg-destructive/10 text-destructive border-destructive/30",
  valid: "bg-success/15 text-success border-success/40",
  invalid: "bg-destructive/10 text-destructive border-destructive/30",
  expired: "bg-destructive/10 text-destructive border-destructive/30",
  limit_reached: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  product_mismatch: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  deactivated: "bg-muted text-muted-foreground border-border",
  suspended_result: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
};

export default function LogiLicenseDetail() {
  const { id } = useParams();
  const [lic, setLic] = useState(null);
  const [activations, setActivations] = useState([]);
  const [checks, setChecks] = useState([]);
  const [tab, setTab] = useState("integrate");

  const publicUrl = `${process.env.REACT_APP_BACKEND_URL}/api/public/license`;

  const load = async () => {
    const [l, a, c] = await Promise.all([
      api.get(`/logi-licenses/${id}`),
      api.get(`/logi-licenses/${id}/activations`),
      api.get(`/logi-licenses/${id}/checks`),
    ]);
    setLic(l.data);
    setActivations(a.data);
    setChecks(c.data.items || []);
  };
  useEffect(() => { load(); }, [id]);

  const copy = async (v) => { try { await navigator.clipboard.writeText(v); toast.success("Copied"); } catch { toast.error("Copy failed"); } };
  const revoke = async () => {
    try { await api.post(`/logi-licenses/${id}/revoke`); toast.success("Revoked"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const reactivate = async () => {
    try { await api.post(`/logi-licenses/${id}/reactivate`); toast.success("Reactivated"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const deactivateDevice = async (aid) => {
    try { await api.delete(`/logi-licenses/${id}/activations/${aid}`); toast.success("Deactivated"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const downloadTutorial = async () => {
    try {
      const res = await api.get(`/logi-licenses/${id}/tutorial/pdf`, { responseType: "blob" });
      const u = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = u;
      a.download = `LogiLicense-${lic?.product_slug || "guide"}-tutorial.pdf`;
      a.click();
      window.URL.revokeObjectURL(u);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!lic) return <div className="text-sm text-muted-foreground">Loading…</div>;

  return (
    <div>
      <Link to="/logi-license" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 mb-4">
        <ArrowLeft className="h-4 w-4" strokeWidth={1.5} /> Back to LogiLicense
      </Link>

      <div className="border-b border-border pb-6 mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="label-eyebrow mb-2 flex items-center gap-2"><Zap className="h-3 w-3" /> LogiLicense</div>
          <h1 className="text-3xl font-display font-semibold tracking-tight">{lic.product_name}</h1>
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <span className="text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 border rounded-sm bg-primary/10 text-primary border-primary/30">
              plan · {lic.plan}
            </span>
            <span className={`text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 border rounded-sm ${STATUS_TONE[lic.status] || ""}`}>
              {lic.status}
            </span>
            {lic.days_left !== null && lic.days_left !== undefined && (
              <span className="text-xs font-mono text-muted-foreground">
                {lic.days_left < 0 ? `Expired ${Math.abs(lic.days_left)}d ago` : `${lic.days_left} days left`}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={downloadTutorial} data-testid="logilicense-download-tutorial">
            <BookOpen className="h-4 w-4 mr-2" strokeWidth={1.5} /> Tutorial PDF
          </Button>
          {lic.status === "active" ? (
            <Button size="sm" variant="outline" onClick={revoke} className="text-destructive">
              <Ban className="h-4 w-4 mr-2" strokeWidth={1.5} /> Revoke
            </Button>
          ) : (
            <Button size="sm" variant="outline" onClick={reactivate}>
              <Check className="h-4 w-4 mr-2" strokeWidth={1.5} /> Reactivate
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={load}>
            <RefreshCw className="h-4 w-4 mr-2" strokeWidth={1.5} /> Refresh
          </Button>
        </div>
      </div>

      {/* Key + stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2 border border-border bg-card p-5">
          <div className="label-eyebrow mb-2">License Key</div>
          <div className="flex items-center gap-2">
            <code className="font-mono text-lg break-all flex-1">{lic.license_key}</code>
            <Button size="sm" variant="outline" onClick={() => copy(lic.license_key)}>
              <Copy className="h-3.5 w-3.5 mr-2" strokeWidth={1.5} /> Copy
            </Button>
          </div>
          {lic.features?.length > 0 && (
            <div className="mt-4">
              <div className="label-eyebrow mb-2">Feature flags</div>
              <div className="flex flex-wrap gap-1.5">
                {lic.features.map((f) => (
                  <span key={f} className="text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 border border-border rounded-sm bg-muted">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}
          {lic.notes && <div className="mt-4 text-sm text-muted-foreground border-t border-border pt-3">{lic.notes}</div>}
        </div>
        <div className="border border-border bg-card divide-y divide-border">
          <Stat k="Activations" v={`${lic.activation_count} / ${lic.max_activations || "∞"}`} />
          <Stat k="Total checks" v={lic.checks_count} />
          <Stat k="Expiry" v={lic.expiry_date ? fmtDate(lic.expiry_date) : "Perpetual"} />
          <Stat k="Issued" v={fmtDate(lic.issued_at)} />
          <Stat k="Product slug" mono v={lic.product_slug || "—"} />
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="integrate">Integration</TabsTrigger>
          <TabsTrigger value="activations">Devices ({activations.length})</TabsTrigger>
          <TabsTrigger value="checks">Verification log ({checks.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="integrate" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Snippet
              title="cURL — Verify"
              language="bash"
              code={`curl -X POST "${publicUrl}/verify" \\
  -H "Content-Type: application/json" \\
  -d '{
    "license_key": "${lic.license_key}",
    "fingerprint": "device-uuid-here",
    "product_slug": "${lic.product_slug || ""}"
  }'`}
              onCopy={copy}
            />
            <Snippet
              title="cURL — Activate"
              language="bash"
              code={`curl -X POST "${publicUrl}/activate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "license_key": "${lic.license_key}",
    "fingerprint": "device-uuid-here",
    "hostname": "my-server.example.com"
  }'`}
              onCopy={copy}
            />
            <Snippet
              title="Node.js"
              language="javascript"
              code={`// On app startup — silent verification
const res = await fetch("${publicUrl}/verify", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    license_key: process.env.LOGI_LICENSE_KEY,
    fingerprint: getMachineId(),          // e.g. node-machine-id
    product_slug: "${lic.product_slug || ""}",
  }),
});
const info = await res.json();
if (info.valid && info.plan !== "trial") {
  app.locals.pro = true;
  app.locals.features = info.features;   // enable Pro features
} else {
  app.locals.pro = false;                // run in trial mode
}`}
              onCopy={copy}
            />
            <Snippet
              title="Python"
              language="python"
              code={`import os, requests, uuid

def verify_license():
    try:
        r = requests.post(
            "${publicUrl}/verify",
            json={
                "license_key": os.getenv("LOGI_LICENSE_KEY", ""),
                "fingerprint": str(uuid.getnode()),
                "product_slug": "${lic.product_slug || ""}",
            },
            timeout=5,
        )
        info = r.json()
    except Exception:
        info = {"valid": False, "plan": "trial"}
    return info

INFO = verify_license()
IS_PRO = INFO.get("valid") and INFO.get("plan") != "trial"
FEATURES = set(INFO.get("features", []))`}
              onCopy={copy}
            />
          </div>
        </TabsContent>

        <TabsContent value="activations" className="mt-4">
          <div className="border border-border bg-card">
            {activations.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">No devices activated yet.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fingerprint</TableHead>
                    <TableHead>Hostname</TableHead>
                    <TableHead>IP</TableHead>
                    <TableHead className="w-32">Activated</TableHead>
                    <TableHead className="w-32">Last seen</TableHead>
                    <TableHead className="text-right w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activations.map((a) => (
                    <TableRow key={a.id} className="hover-row">
                      <TableCell className="font-mono text-xs">{a.fingerprint}</TableCell>
                      <TableCell className="text-xs">{a.hostname || "—"}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{a.last_ip || a.ip || "—"}</TableCell>
                      <TableCell className="text-xs">{fmtRelative(a.activated_at)}</TableCell>
                      <TableCell className="text-xs">{a.last_seen_at ? fmtRelative(a.last_seen_at) : "—"}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" className="text-destructive" onClick={() => deactivateDevice(a.id)}>
                          <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        <TabsContent value="checks" className="mt-4">
          <div className="border border-border bg-card">
            {checks.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">No verification calls yet.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-40">When</TableHead>
                    <TableHead className="w-32">Result</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Fingerprint</TableHead>
                    <TableHead className="w-32">IP</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {checks.map((c) => (
                    <TableRow key={c.id} className="hover-row">
                      <TableCell className="text-xs">{fmtDateTime(c.timestamp)}</TableCell>
                      <TableCell>
                        <span className={`text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 border rounded-sm ${STATUS_TONE[c.result] || "bg-muted text-muted-foreground border-border"}`}>
                          {c.result}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs">{c.message}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground truncate max-w-[200px]">{c.fingerprint || "—"}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{c.ip || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Stat({ k, v, mono }) {
  return (
    <div className="px-5 py-3 flex items-center justify-between">
      <div className="label-eyebrow">{k}</div>
      <div className={`text-sm font-medium ${mono ? "font-mono" : ""}`}>{v}</div>
    </div>
  );
}

function Snippet({ title, language, code, onCopy }) {
  return (
    <div className="border border-border bg-card">
      <div className="px-4 py-2 border-b border-border flex items-center justify-between">
        <div className="font-display font-medium text-sm">{title}</div>
        <div className="flex items-center gap-2">
          <span className="label-eyebrow">{language}</span>
          <Button size="sm" variant="ghost" onClick={() => onCopy(code)}>
            <Copy className="h-3.5 w-3.5" strokeWidth={1.5} />
          </Button>
        </div>
      </div>
      <pre className="p-4 text-xs font-mono overflow-x-auto leading-relaxed bg-muted/30">
{code}
      </pre>
    </div>
  );
}
