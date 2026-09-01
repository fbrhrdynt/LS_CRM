import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search, Pencil, Trash2, Eye, EyeOff, Copy, KeyRound, Sparkles } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/contexts/AuthContext";
import { fmtDate } from "@/lib/format";

const CATEGORY_STYLES = {
  Starlink: "bg-primary/10 text-primary border-primary/30",
  "Google Workspace": "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  "Microsoft 365": "bg-primary/10 text-primary border-primary/30",
  Cloudflare: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  Domain: "bg-success/15 text-success border-success/40",
  Hosting: "bg-success/15 text-success border-success/40",
  VPS: "bg-success/15 text-success border-success/40",
  cPanel: "bg-success/15 text-success border-success/40",
  VPN: "bg-primary/10 text-primary border-primary/30",
  MikroTik: "bg-primary/10 text-primary border-primary/30",
  UniFi: "bg-primary/10 text-primary border-primary/30",
  Synology: "bg-primary/10 text-primary border-primary/30",
  CCTV: "bg-muted text-muted-foreground border-border",
  Custom: "bg-muted text-muted-foreground border-border",
};

const EMPTY = {
  name: "", category: "Custom", customer_id: "", project_id: "",
  username: "", email: "", password: "", login_url: "",
  recovery_email: "", recovery_phone: "",
  registration_number: "", license_key: "", subscription_id: "",
  api_key: "", secret_key: "", expiry_date: "", renewal_date: "", notes: "",
};

export default function Accounts() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [categories, setCategories] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [dlgOpen, setDlgOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [revealed, setRevealed] = useState({}); // id -> {password, api_key, secret_key}
  const [showPwd, setShowPwd] = useState(false);

  const load = async () => {
    const params = { q, page, per_page: 20 };
    if (cat !== "all") params.category = cat;
    const { data } = await api.get("/accounts", { params });
    setRows(data.items); setTotalPages(data.total_pages);
  };
  useEffect(() => { load(); }, [q, cat, page]); // eslint-disable-line
  useEffect(() => {
    api.get("/accounts/categories").then((r) => setCategories(r.data));
    api.get("/customers/all").then((r) => setCustomers(r.data));
    api.get("/projects/all").then((r) => setProjects(r.data));
  }, []);

  const openNew = () => { setForm(EMPTY); setEditingId(null); setShowPwd(false); setDlgOpen(true); };
  const openEdit = async (r) => {
    setEditingId(r.id); setShowPwd(false);
    // fetch full then reveal secrets on demand
    const { data: full } = await api.get(`/accounts/${r.id}`);
    setForm({ ...EMPTY, ...full, password: "", api_key: "", secret_key: "" });
    setDlgOpen(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      // If editing and secret fields empty, strip them so we don't overwrite
      const payload = { ...form };
      if (editingId) {
        for (const f of ["password", "api_key", "secret_key"]) {
          if (payload[f] === "") delete payload[f];
        }
      }
      // Normalize placeholders
      if (payload.customer_id === "__none") payload.customer_id = "";
      if (payload.project_id === "__none") payload.project_id = "";
      if (editingId) { await api.put(`/accounts/${editingId}`, payload); toast.success("Account updated"); }
      else { await api.post("/accounts", payload); toast.success("Account created"); }
      setDlgOpen(false); load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const doDelete = async () => {
    try { await api.delete(`/accounts/${toDelete.id}`); toast.success("Deleted"); setToDelete(null); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const generatePwd = async (targetField = "password") => {
    const { data } = await api.post("/accounts/generate-password", null, { params: { length: 16 } });
    setForm((f) => ({ ...f, [targetField]: data.password }));
    setShowPwd(true);
    toast.success("Strong password generated");
  };

  const reveal = async (id) => {
    if (revealed[id]) {
      setRevealed((r) => { const c = { ...r }; delete c[id]; return c; });
      return;
    }
    try {
      const { data } = await api.get(`/accounts/${id}/reveal`);
      setRevealed((r) => ({ ...r, [id]: data }));
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const copyToClipboard = async (label, value) => {
    if (!value) return toast.error(`No ${label} to copy`);
    try {
      await navigator.clipboard.writeText(value);
      toast.success(`${label} copied`);
    } catch { toast.error("Copy failed"); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Operations"
        title="Credential Vault"
        description="Company & customer accounts, encrypted at rest with AES-256. Every reveal is audited."
        actions={<Button size="sm" onClick={openNew} data-testid="account-new-button"><Plus className="h-4 w-4 mr-2" strokeWidth={1.5} />New account</Button>}
      />

      <div className="border border-border bg-card">
        <div className="p-3 border-b border-border flex flex-col md:flex-row gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
            <Input placeholder="Search name, username, URL…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} className="pl-8" data-testid="account-search-input" />
          </div>
          <Select value={cat} onValueChange={(v) => { setPage(1); setCat(v); }}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        {rows.length === 0 ? (
          <EmptyState icon={KeyRound} title="Vault is empty" description="Add your first credential to keep it safely encrypted."
            action={<Button size="sm" onClick={openNew}><Plus className="h-4 w-4 mr-2" />New account</Button>} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
            {rows.map((r) => {
              const rev = revealed[r.id];
              const catStyle = CATEGORY_STYLES[r.category] || CATEGORY_STYLES.Custom;
              return (
                <div key={r.id} className="border border-border bg-background flex flex-col" data-testid={`account-card-${r.id}`}>
                  <div className="p-4 border-b border-border flex items-start justify-between">
                    <div className="min-w-0">
                      <div className="font-display font-medium truncate">{r.name}</div>
                      <div className="text-xs text-muted-foreground truncate">{r.customer_name || "Internal"}</div>
                    </div>
                    <span className={`text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 border rounded-sm ${catStyle}`}>{r.category}</span>
                  </div>

                  <div className="p-4 space-y-2 flex-1">
                    <VaultRow label="Username" value={r.username} onCopy={() => copyToClipboard("Username", r.username)} testId={`account-${r.id}-username`} />
                    <VaultRow label="Email" value={r.email} onCopy={() => copyToClipboard("Email", r.email)} />
                    <VaultRow
                      label="Password"
                      value={rev ? rev.password : (r.has_password ? "••••••••••" : "")}
                      mono
                      hidden={!rev && r.has_password}
                      onCopy={() => copyToClipboard("Password", rev?.password || "")}
                      onToggle={r.has_password ? () => reveal(r.id) : null}
                      isRevealed={!!rev}
                      testId={`account-${r.id}-password`}
                    />
                    {r.login_url && (
                      <div className="text-xs">
                        <a href={r.login_url} target="_blank" rel="noreferrer" className="text-primary hover:underline break-all">{r.login_url}</a>
                      </div>
                    )}
                    {r.expiry_date && (
                      <div className="text-xs text-muted-foreground pt-2 border-t border-border">
                        Expires <span className="text-foreground font-medium">{fmtDate(r.expiry_date)}</span>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-border p-2 flex items-center justify-end gap-1">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(r)}><Pencil className="h-4 w-4" strokeWidth={1.5} /></Button>
                    {isAdmin && <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setToDelete(r)}><Trash2 className="h-4 w-4" strokeWidth={1.5} /></Button>}
                  </div>
                </div>
              );
            })}
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

      {/* Form dialog */}
      <Dialog open={dlgOpen} onOpenChange={setDlgOpen}>
        <DialogContent className="sm:max-w-[720px] max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-display">{editingId ? "Edit Account" : "New Account"}</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="grid grid-cols-2 gap-3">
            <Field label="Name *" span={2}>
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="account-form-name" />
            </Field>
            <Field label="Category">
              <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
            <Field label="Customer">
              <Select value={form.customer_id || "__none"} onValueChange={(v) => setForm({ ...form, customer_id: v === "__none" ? "" : v })}>
                <SelectTrigger><SelectValue placeholder="Internal" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none">— Internal —</SelectItem>
                  {customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Project">
              <Select value={form.project_id || "__none"} onValueChange={(v) => setForm({ ...form, project_id: v === "__none" ? "" : v })}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none">— None —</SelectItem>
                  {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Login URL"><Input value={form.login_url || ""} onChange={(e) => setForm({ ...form, login_url: e.target.value })} placeholder="https://…" /></Field>

            <Field label="Username"><Input className="font-mono" value={form.username || ""} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Field>
            <Field label="Email"><Input className="font-mono" value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>

            <Field span={2} label={editingId ? "Password (leave blank to keep current)" : "Password"}>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    className="font-mono"
                    type={showPwd ? "text" : "password"}
                    value={form.password || ""}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    data-testid="account-form-password"
                  />
                  <button type="button" onClick={() => setShowPwd((s) => !s)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1">
                    {showPwd ? <EyeOff className="h-4 w-4" strokeWidth={1.5} /> : <Eye className="h-4 w-4" strokeWidth={1.5} />}
                  </button>
                </div>
                <Button type="button" variant="outline" onClick={() => generatePwd("password")} data-testid="account-form-generate-password">
                  <Sparkles className="h-4 w-4 mr-2" strokeWidth={1.5} /> Generate
                </Button>
              </div>
            </Field>

            <Field label="Recovery Email"><Input value={form.recovery_email || ""} onChange={(e) => setForm({ ...form, recovery_email: e.target.value })} /></Field>
            <Field label="Recovery Phone"><Input value={form.recovery_phone || ""} onChange={(e) => setForm({ ...form, recovery_phone: e.target.value })} /></Field>

            <Field label="Registration Number"><Input className="font-mono" value={form.registration_number || ""} onChange={(e) => setForm({ ...form, registration_number: e.target.value })} /></Field>
            <Field label="License Key"><Input className="font-mono" value={form.license_key || ""} onChange={(e) => setForm({ ...form, license_key: e.target.value })} /></Field>

            <Field label="Subscription ID"><Input className="font-mono" value={form.subscription_id || ""} onChange={(e) => setForm({ ...form, subscription_id: e.target.value })} /></Field>
            <Field label={editingId ? "API Key (leave blank to keep)" : "API Key"}><Input className="font-mono" value={form.api_key || ""} onChange={(e) => setForm({ ...form, api_key: e.target.value })} /></Field>

            <Field label={editingId ? "Secret Key (blank keeps)" : "Secret Key"} span={2}><Input className="font-mono" value={form.secret_key || ""} onChange={(e) => setForm({ ...form, secret_key: e.target.value })} /></Field>

            <Field label="Expiry Date"><Input type="date" value={form.expiry_date || ""} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} /></Field>
            <Field label="Renewal Date"><Input type="date" value={form.renewal_date || ""} onChange={(e) => setForm({ ...form, renewal_date: e.target.value })} /></Field>

            <Field label="Notes" span={2}><Textarea value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} /></Field>

            <DialogFooter className="col-span-2 mt-2">
              <Button type="button" variant="outline" onClick={() => setDlgOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={busy} data-testid="account-form-submit">{busy ? "Saving..." : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete account?</AlertDialogTitle>
            <AlertDialogDescription>Delete credential vault entry <b>{toDelete?.name}</b>? This is irreversible.</AlertDialogDescription>
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

function VaultRow({ label, value, mono, hidden, onCopy, onToggle, isRevealed, testId }) {
  return (
    <div className="flex items-center gap-2 group">
      <div className="w-16 label-eyebrow">{label}</div>
      <div className={`flex-1 min-w-0 truncate text-xs ${mono ? "font-mono" : ""}`} data-testid={testId}>
        {value || <span className="text-muted-foreground">—</span>}
      </div>
      {onToggle && (
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onToggle} data-testid={`${testId}-toggle`}>
          {isRevealed ? <EyeOff className="h-3.5 w-3.5" strokeWidth={1.5} /> : <Eye className="h-3.5 w-3.5" strokeWidth={1.5} />}
        </Button>
      )}
      {value && (
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onCopy} data-testid={`${testId}-copy`}>
          <Copy className="h-3.5 w-3.5" strokeWidth={1.5} />
        </Button>
      )}
    </div>
  );
}

function Field({ label, span = 1, children }) {
  return (
    <div className={`space-y-1.5 ${span === 2 ? "col-span-2" : ""}`}>
      <Label className="text-xs uppercase tracking-widest">{label}</Label>
      {children}
    </div>
  );
}
