import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search, Pencil, Trash2, BadgeCheck } from "lucide-react";
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/contexts/AuthContext";
import { fmtDate } from "@/lib/format";

const EMPTY = {
  product_id: "", product_name: "", customer_id: "", registration_number: "",
  license_code: "", expiry_date: "", renewal_date: "", notes: "",
};

export default function Licenses() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [q, setQ] = useState("");
  const [within, setWithin] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [dlgOpen, setDlgOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);

  const load = async () => {
    const { data } = await api.get("/licenses", { params: { q, within_days: within, page, per_page: 20 } });
    setRows(data.items); setTotalPages(data.total_pages);
  };
  useEffect(() => { load(); }, [q, within, page]); // eslint-disable-line
  useEffect(() => {
    api.get("/customers/all").then((r) => setCustomers(r.data));
    api.get("/products/all").then((r) => setProducts(r.data));
  }, []);

  const openNew = () => { setForm(EMPTY); setEditingId(null); setDlgOpen(true); };
  const openEdit = (r) => { setForm({ ...EMPTY, ...r }); setEditingId(r.id); setDlgOpen(true); };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form };
      if (payload.customer_id === "__none") payload.customer_id = "";
      if (payload.product_id === "__none") payload.product_id = "";
      if (editingId) { await api.put(`/licenses/${editingId}`, payload); toast.success("License updated"); }
      else { await api.post("/licenses", payload); toast.success("License created"); }
      setDlgOpen(false); load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const doDelete = async () => {
    try { await api.delete(`/licenses/${toDelete.id}`); toast.success("Deleted"); setToDelete(null); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Operations"
        title="Registration & License Management"
        description="Never miss a renewal — with 30/15/7 day expiry countdowns and reminders."
        actions={<Button size="sm" onClick={openNew} data-testid="license-new-button"><Plus className="h-4 w-4 mr-2" strokeWidth={1.5} />New license</Button>}
      />

      <div className="border border-border bg-card">
        <div className="p-3 border-b border-border flex flex-col md:flex-row gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
            <Input placeholder="Search product, license, registration…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} className="pl-8" />
          </div>
          <Tabs value={String(within)} onValueChange={(v) => { setPage(1); setWithin(Number(v)); }}>
            <TabsList>
              <TabsTrigger value="0">All</TabsTrigger>
              <TabsTrigger value="30">≤ 30 days</TabsTrigger>
              <TabsTrigger value="15">≤ 15 days</TabsTrigger>
              <TabsTrigger value="7">≤ 7 days</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {rows.length === 0 ? (
          <EmptyState icon={BadgeCheck} title="No licenses tracked" description="Register a license or product code to enable expiry alerts."
            action={<Button size="sm" onClick={openNew}><Plus className="h-4 w-4 mr-2" />New license</Button>} />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product / License</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Registration</TableHead>
                  <TableHead>License Code</TableHead>
                  <TableHead className="w-28">Expiry</TableHead>
                  <TableHead className="w-24">Days left</TableHead>
                  <TableHead className="text-right w-24">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => {
                  const dl = r.days_left;
                  const tone = dl === null ? "text-muted-foreground" :
                    dl < 0 ? "text-destructive" :
                    dl <= 7 ? "text-destructive" :
                    dl <= 30 ? "text-[hsl(var(--warning))]" : "text-success";
                  return (
                    <TableRow key={r.id} className="hover-row">
                      <TableCell className="font-medium">{r.product_name || "—"}</TableCell>
                      <TableCell>{r.customer_name || "—"}</TableCell>
                      <TableCell className="font-mono text-xs">{r.registration_number || "—"}</TableCell>
                      <TableCell className="font-mono text-xs">{r.license_code || "—"}</TableCell>
                      <TableCell className="text-xs">{fmtDate(r.expiry_date)}</TableCell>
                      <TableCell className={`font-mono text-xs ${tone}`}>{dl === null ? "—" : `${dl}d`}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" onClick={() => openEdit(r)}><Pencil className="h-4 w-4" strokeWidth={1.5} /></Button>
                        {isAdmin && <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setToDelete(r)}><Trash2 className="h-4 w-4" strokeWidth={1.5} /></Button>}
                      </TableCell>
                    </TableRow>
                  );
                })}
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

      <Dialog open={dlgOpen} onOpenChange={setDlgOpen}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader><DialogTitle className="font-display">{editingId ? "Edit License" : "New License"}</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="grid grid-cols-2 gap-3">
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Product</Label>
              <Select value={form.product_id || "__none"} onValueChange={(v) => {
                if (v === "__none") return setForm({ ...form, product_id: "", product_name: form.product_name });
                const p = products.find((x) => x.id === v);
                setForm({ ...form, product_id: v, product_name: p?.name || "" });
              }}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none">— Custom name below —</SelectItem>
                  {products.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Product Name (display)</Label>
              <Input value={form.product_name || ""} onChange={(e) => setForm({ ...form, product_name: e.target.value })} />
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Customer</Label>
              <Select value={form.customer_id || "__none"} onValueChange={(v) => setForm({ ...form, customer_id: v === "__none" ? "" : v })}>
                <SelectTrigger><SelectValue placeholder="Internal" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none">— Internal —</SelectItem>
                  {customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Registration Number</Label>
              <Input className="font-mono" value={form.registration_number || ""} onChange={(e) => setForm({ ...form, registration_number: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">License Code</Label>
              <Input className="font-mono" value={form.license_code || ""} onChange={(e) => setForm({ ...form, license_code: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Expiry Date</Label>
              <Input type="date" value={form.expiry_date || ""} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Renewal Date</Label>
              <Input type="date" value={form.renewal_date || ""} onChange={(e) => setForm({ ...form, renewal_date: e.target.value })} />
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Notes</Label>
              <Textarea value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} />
            </div>
            <DialogFooter className="col-span-2">
              <Button type="button" variant="outline" onClick={() => setDlgOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={busy}>{busy ? "Saving..." : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete license?</AlertDialogTitle>
            <AlertDialogDescription>Delete license {toDelete?.license_code || toDelete?.product_name}?</AlertDialogDescription>
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
