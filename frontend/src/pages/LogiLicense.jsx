import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Plus, Search, Trash2, Zap, Copy, ExternalLink, BookOpen } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/contexts/AuthContext";
import { fmtDate } from "@/lib/format";

const PLANS = ["trial", "starter", "pro", "premium", "enterprise", "lifetime"];
const STATUS_TONE = {
  active: "bg-success/15 text-success border-success/40",
  suspended: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  revoked: "bg-destructive/10 text-destructive border-destructive/30",
};

const EMPTY = {
  product_name: "", product_slug: "", plan: "pro", features: [],
  customer_id: "", project_id: "", max_activations: 1, expiry_date: "", notes: "",
};

export default function LogiLicense() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [plan, setPlan] = useState("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [dlgOpen, setDlgOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [featuresInput, setFeaturesInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [issuedKey, setIssuedKey] = useState(null);

  const load = async () => {
    const params = { q, page, per_page: 20 };
    if (status !== "all") params.status = status;
    if (plan !== "all") params.plan = plan;
    const { data } = await api.get("/logi-licenses", { params });
    setRows(data.items); setTotalPages(data.total_pages);
  };
  useEffect(() => { load(); }, [q, status, plan, page]); // eslint-disable-line
  useEffect(() => {
    api.get("/customers/all").then((r) => setCustomers(r.data));
    api.get("/projects/all").then((r) => setProjects(r.data));
  }, []);

  const openNew = () => {
    setForm(EMPTY); setFeaturesInput(""); setDlgOpen(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = {
        ...form,
        features: featuresInput.split(",").map((s) => s.trim()).filter(Boolean),
        max_activations: Number(form.max_activations || 1),
      };
      if (payload.customer_id === "__none") payload.customer_id = "";
      if (payload.project_id === "__none") payload.project_id = "";
      const { data } = await api.post("/logi-licenses", payload);
      setIssuedKey(data);
      setDlgOpen(false);
      toast.success(`License issued`);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const doDelete = async () => {
    try { await api.delete(`/logi-licenses/${toDelete.id}`); toast.success("Deleted"); setToDelete(null); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const copy = async (v) => {
    try { await navigator.clipboard.writeText(v); toast.success("Copied"); } catch { toast.error("Copy failed"); }
  };

  const downloadSetupGuide = async () => {
    try {
      const res = await api.get("/logi-licenses/setup-guide/pdf", { responseType: "blob" });
      const u = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = u; a.download = "LogiLicense-Setup-Guide.pdf"; a.click();
      window.URL.revokeObjectURL(u);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Operations"
        title="LogiLicense"
        description="Issue and enforce Pro/Premium license keys for your external products — websites, IoT devices, plugins. Every external verification is silently audited."
        actions={
          <>
            <Button size="sm" variant="outline" onClick={downloadSetupGuide} data-testid="logilicense-setup-guide-button">
              <BookOpen className="h-4 w-4 mr-2" strokeWidth={1.5} /> Setup Guide (PDF)
            </Button>
            <Button size="sm" onClick={openNew} data-testid="logilicense-new-button">
              <Plus className="h-4 w-4 mr-2" strokeWidth={1.5} /> Issue license
            </Button>
          </>
        }
      />

      {/* Public API info banner */}
      <div className="border border-primary/40 bg-primary/5 p-4 mb-6 flex flex-col md:flex-row md:items-center gap-3">
        <Zap className="h-5 w-5 text-primary shrink-0" strokeWidth={1.5} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium">Public verification endpoint</div>
          <div className="text-xs text-muted-foreground font-mono truncate">
            {process.env.REACT_APP_BACKEND_URL}/api/public/license/verify
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={() => copy(`${process.env.REACT_APP_BACKEND_URL}/api/public/license/verify`)}>
          <Copy className="h-3.5 w-3.5 mr-2" strokeWidth={1.5} /> Copy URL
        </Button>
      </div>

      <div className="border border-border bg-card">
        <div className="p-3 border-b border-border flex flex-col md:flex-row gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
            <Input placeholder="Search product, slug, key…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} className="pl-8" data-testid="logilicense-search-input" />
          </div>
          <Select value={plan} onValueChange={(v) => { setPage(1); setPlan(v); }}>
            <SelectTrigger className="w-40"><SelectValue placeholder="Plan" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All plans</SelectItem>
              {PLANS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={(v) => { setPage(1); setStatus(v); }}>
            <SelectTrigger className="w-40"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="suspended">Suspended</SelectItem>
              <SelectItem value="revoked">Revoked</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {rows.length === 0 ? (
          <EmptyState icon={Zap} title="No licenses issued yet"
            description="Issue your first key to lock Pro features to a specific product & activation limit."
            action={<Button size="sm" onClick={openNew}><Plus className="h-4 w-4 mr-2" />Issue license</Button>} />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>License Key</TableHead>
                  <TableHead className="w-24">Plan</TableHead>
                  <TableHead className="w-24">Status</TableHead>
                  <TableHead className="w-28 text-right">Activations</TableHead>
                  <TableHead className="w-28">Expiry</TableHead>
                  <TableHead className="w-24 text-right">Checks</TableHead>
                  <TableHead className="text-right w-24">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id} className="hover-row">
                    <TableCell>
                      <Link to={`/logi-license/${r.id}`} className="hover:text-primary hover:underline font-medium">
                        {r.product_name}
                      </Link>
                      {r.customer_name && <div className="text-xs text-muted-foreground">{r.customer_name}</div>}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs">{r.license_key}</span>
                        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => copy(r.license_key)}>
                          <Copy className="h-3.5 w-3.5" strokeWidth={1.5} />
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 border rounded-sm bg-primary/10 text-primary border-primary/30">{r.plan}</span>
                    </TableCell>
                    <TableCell>
                      <span className={`text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 border rounded-sm ${STATUS_TONE[r.status] || ""}`}>
                        {r.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-xs">
                      {r.activation_count} / {r.max_activations || "∞"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {r.expiry_date ? (
                        <span className={r.days_left !== null && r.days_left < 0 ? "text-destructive" : ""}>
                          {fmtDate(r.expiry_date)}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">Perpetual</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-xs">{r.checks_count}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" asChild>
                        <Link to={`/logi-license/${r.id}`}><ExternalLink className="h-4 w-4" strokeWidth={1.5} /></Link>
                      </Button>
                      {isAdmin && (
                        <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setToDelete(r)}>
                          <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="border-t border-border p-3 flex items-center justify-between text-sm">
            <div className="text-muted-foreground">Page {page} of {totalPages}</div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
            </div>
          </div>
        )}
      </div>

      {/* Issue form */}
      <Dialog open={dlgOpen} onOpenChange={setDlgOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-display">Issue new license</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="grid grid-cols-2 gap-3">
            <F label="Product Name *" span={2}>
              <Input required value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })}
                placeholder="e.g. MyIoT Dashboard" data-testid="logilicense-form-product-name" />
            </F>
            <F label="Product Slug" hint="url-safe identifier">
              <Input value={form.product_slug} onChange={(e) => setForm({ ...form, product_slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })}
                placeholder="e.g. myiot" />
            </F>
            <F label="Plan">
              <Select value={form.plan} onValueChange={(v) => setForm({ ...form, plan: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{PLANS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
              </Select>
            </F>
            <F label="Feature Flags" hint="comma-separated" span={2}>
              <Input value={featuresInput} onChange={(e) => setFeaturesInput(e.target.value)}
                placeholder="e.g. cloud_sync, unlimited_devices, custom_theme" />
            </F>
            <F label="Customer">
              <Select value={form.customer_id || "__none"} onValueChange={(v) => setForm({ ...form, customer_id: v === "__none" ? "" : v })}>
                <SelectTrigger><SelectValue placeholder="Internal" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none">— Internal —</SelectItem>
                  {customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}
                </SelectContent>
              </Select>
            </F>
            <F label="Project">
              <Select value={form.project_id || "__none"} onValueChange={(v) => setForm({ ...form, project_id: v === "__none" ? "" : v })}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none">— None —</SelectItem>
                  {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </F>
            <F label="Max Activations" hint="0 = unlimited">
              <Input type="number" min="0" value={form.max_activations} onChange={(e) => setForm({ ...form, max_activations: e.target.value })} />
            </F>
            <F label="Expiry Date" hint="empty = perpetual">
              <Input type="date" value={form.expiry_date || ""} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} />
            </F>
            <F label="Notes" span={2}>
              <Textarea rows={2} value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </F>

            <DialogFooter className="col-span-2 mt-2">
              <Button type="button" variant="outline" onClick={() => setDlgOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={busy} data-testid="logilicense-form-submit">{busy ? "Issuing..." : "Issue license"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Newly issued key */}
      <Dialog open={!!issuedKey} onOpenChange={(o) => !o && setIssuedKey(null)}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader><DialogTitle className="font-display">License issued 🎉</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <div className="label-eyebrow mb-2">Product</div>
              <div className="font-medium">{issuedKey?.product_name}</div>
            </div>
            <div>
              <div className="label-eyebrow mb-2">License Key</div>
              <div className="border border-border bg-muted/40 p-3 flex items-center justify-between gap-2">
                <code className="font-mono text-sm break-all">{issuedKey?.license_key}</code>
                <Button size="sm" variant="outline" onClick={() => copy(issuedKey?.license_key)}>
                  <Copy className="h-3.5 w-3.5 mr-2" strokeWidth={1.5} /> Copy
                </Button>
              </div>
              <div className="text-xs text-muted-foreground mt-2">
                Store this key securely — you can view it again in the detail page.
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setIssuedKey(null)}>Done</Button>
              <Button asChild>
                <Link to={`/logi-license/${issuedKey?.id}`} onClick={() => setIssuedKey(null)}>
                  Open detail <ExternalLink className="h-4 w-4 ml-2" strokeWidth={1.5} />
                </Link>
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete license?</AlertDialogTitle>
            <AlertDialogDescription>
              Delete <b>{toDelete?.license_key}</b>? All external clients using this key will instantly fall back to trial.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={doDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function F({ label, hint, span = 1, children }) {
  return (
    <div className={`space-y-1.5 ${span === 2 ? "col-span-2" : ""}`}>
      <Label className="text-xs uppercase tracking-widest">
        {label}
        {hint && <span className="ml-2 normal-case tracking-normal text-[10px] text-muted-foreground">({hint})</span>}
      </Label>
      {children}
    </div>
  );
}
