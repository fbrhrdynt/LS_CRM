import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search, Pencil, Trash2, Download, Upload, Package as PackageIcon, FileText } from "lucide-react";
import api, { API, formatApiError, getToken } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAuth } from "@/contexts/AuthContext";
import { fmtMoney } from "@/lib/format";

const EMPTY = {
  code: "", name: "", product_type: "goods", category: "", brand: "", description: "",
  unit: "pcs", selling_price: 0, purchase_price: 0, tax_percent: 11, status: "active",
  sku: "", stock: 0, warranty: "", sla: "", duration: "", support_period: "",
};

export default function Products() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [cats, setCats] = useState([]);
  const [q, setQ] = useState("");
  const [type, setType] = useState("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [dlgOpen, setDlgOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [catDlgOpen, setCatDlgOpen] = useState(false);
  const [newCatName, setNewCatName] = useState("");

  const load = async () => {
    try {
      const params = { q, page, per_page: 20 };
      if (type !== "all") params.product_type = type;
      const { data } = await api.get("/products", { params });
      setRows(data.items);
      setTotalPages(data.total_pages);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };
  const loadCats = async () => {
    const { data } = await api.get("/products/categories");
    setCats(data);
  };
  useEffect(() => { load(); }, [q, page, type]); // eslint-disable-line
  useEffect(() => { loadCats(); }, []);

  const openNew = () => { setForm(EMPTY); setEditingId(null); setDlgOpen(true); };
  const openEdit = (r) => { setForm({ ...EMPTY, ...r }); setEditingId(r.id); setDlgOpen(true); };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form,
        selling_price: Number(form.selling_price),
        purchase_price: Number(form.purchase_price),
        tax_percent: Number(form.tax_percent),
        stock: Number(form.stock || 0),
      };
      if (editingId) {
        await api.put(`/products/${editingId}`, payload);
        toast.success("Product updated");
      } else {
        await api.post("/products", payload);
        toast.success("Product created");
      }
      setDlgOpen(false);
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally { setBusy(false); }
  };

  const doDelete = async () => {
    try {
      await api.delete(`/products/${toDelete.id}`);
      toast.success("Deleted");
      setToDelete(null);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const addCategory = async () => {
    if (!newCatName.trim()) return;
    try {
      await api.post("/products/categories", { name: newCatName.trim() });
      setNewCatName("");
      loadCats();
      toast.success("Category added");
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const download = async (url, filename) => {
    try {
      const res = await api.get(url, { responseType: "blob" });
      const u = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = u; a.download = filename; a.click();
      window.URL.revokeObjectURL(u);
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const importXlsx = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${API}/products/import/xlsx`, {
        method: "POST", body: fd,
        headers: { Authorization: `Bearer ${getToken()}` }, credentials: "include",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Import failed");
      toast.success(`Imported ${data.created}, skipped ${data.skipped}`);
      load();
    } catch (err) { toast.error(err.message); }
    finally { e.target.value = ""; }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Sales"
        title="Products"
        description="Goods and services offered to your customers. Includes SKU, pricing, tax and stock information."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setCatDlgOpen(true)} data-testid="product-manage-categories">
              Categories
            </Button>
            <label className="cursor-pointer">
              <input type="file" accept=".xlsx" className="hidden" onChange={importXlsx} />
              <Button variant="outline" size="sm" asChild>
                <span><Upload className="h-4 w-4 mr-2" strokeWidth={1.5} />Import</span>
              </Button>
            </label>
            <Button variant="outline" size="sm" onClick={() => download("/products/export/xlsx", "products.xlsx")}>
              <Download className="h-4 w-4 mr-2" strokeWidth={1.5} />Excel
            </Button>
            <Button variant="outline" size="sm" onClick={() => download("/products/export/pdf", "products.pdf")}>
              <FileText className="h-4 w-4 mr-2" strokeWidth={1.5} />PDF
            </Button>
            <Button size="sm" onClick={openNew} data-testid="product-new-button">
              <Plus className="h-4 w-4 mr-2" strokeWidth={1.5} />New product
            </Button>
          </>
        }
      />

      <div className="border border-border bg-card">
        <div className="p-3 border-b border-border flex flex-col md:flex-row items-stretch md:items-center gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
            <Input placeholder="Search name, code, SKU…" value={q}
              onChange={(e) => { setPage(1); setQ(e.target.value); }} className="pl-8" data-testid="product-search-input" />
          </div>
          <Tabs value={type} onValueChange={(v) => { setPage(1); setType(v); }}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="goods">Goods</TabsTrigger>
              <TabsTrigger value="service">Services</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {rows.length === 0 ? (
          <EmptyState icon={PackageIcon} title="No products yet" description="Add products or services to start creating quotations." action={<Button onClick={openNew} size="sm"><Plus className="h-4 w-4 mr-2" />New product</Button>} />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-32">Code</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Unit</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead className="text-right">Stock</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right w-24">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id} className="hover-row">
                    <TableCell className="font-mono text-xs">{r.code}</TableCell>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell><span className="label-eyebrow">{r.product_type}</span></TableCell>
                    <TableCell>{r.category || "—"}</TableCell>
                    <TableCell>{r.unit}</TableCell>
                    <TableCell className="text-right tabular-nums">{fmtMoney(r.selling_price)}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.product_type === "goods" ? r.stock : "—"}</TableCell>
                    <TableCell><StatusBadge status={r.status} /></TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(r)}><Pencil className="h-4 w-4" strokeWidth={1.5} /></Button>
                      {isAdmin && (
                        <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setToDelete(r)}><Trash2 className="h-4 w-4" strokeWidth={1.5} /></Button>
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

      {/* Form dialog */}
      <Dialog open={dlgOpen} onOpenChange={setDlgOpen}>
        <DialogContent className="sm:max-w-[720px] max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-display">{editingId ? "Edit Product" : "New Product"}</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="grid grid-cols-2 gap-3">
            <div className="col-span-2 grid grid-cols-3 gap-3">
              <FieldWrap label="Product Code" hint="auto if blank">
                <Input value={form.code || ""} onChange={(e) => setForm({ ...form, code: e.target.value })} />
              </FieldWrap>
              <FieldWrap label="Type" required>
                <Select value={form.product_type} onValueChange={(v) => setForm({ ...form, product_type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="goods">Goods</SelectItem>
                    <SelectItem value="service">Service</SelectItem>
                  </SelectContent>
                </Select>
              </FieldWrap>
              <FieldWrap label="Status">
                <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </FieldWrap>
            </div>
            <FieldWrap label="Name" required span={2}>
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="product-form-name" />
            </FieldWrap>
            <FieldWrap label="Category">
              <Select value={form.category || "__none"} onValueChange={(v) => setForm({ ...form, category: v === "__none" ? "" : v })}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none">No category</SelectItem>
                  {cats.map((c) => (<SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>))}
                </SelectContent>
              </Select>
            </FieldWrap>
            <FieldWrap label="Brand">
              <Input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
            </FieldWrap>
            <FieldWrap label="Description" span={2}>
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
            </FieldWrap>
            <FieldWrap label="Unit"><Input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} /></FieldWrap>
            <FieldWrap label="Tax %"><Input type="number" step="0.01" value={form.tax_percent} onChange={(e) => setForm({ ...form, tax_percent: e.target.value })} /></FieldWrap>
            <FieldWrap label="Selling Price"><Input type="number" step="0.01" value={form.selling_price} onChange={(e) => setForm({ ...form, selling_price: e.target.value })} /></FieldWrap>
            <FieldWrap label="Purchase Price"><Input type="number" step="0.01" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} /></FieldWrap>

            {form.product_type === "goods" && (
              <>
                <FieldWrap label="SKU"><Input value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} /></FieldWrap>
                <FieldWrap label="Stock"><Input type="number" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} /></FieldWrap>
                <FieldWrap label="Warranty" span={2}><Input value={form.warranty} onChange={(e) => setForm({ ...form, warranty: e.target.value })} placeholder="e.g. 1 year manufacturer" /></FieldWrap>
              </>
            )}
            {form.product_type === "service" && (
              <>
                <FieldWrap label="SLA"><Input value={form.sla} onChange={(e) => setForm({ ...form, sla: e.target.value })} placeholder="e.g. 99.9% uptime" /></FieldWrap>
                <FieldWrap label="Duration"><Input value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} placeholder="e.g. 12 months" /></FieldWrap>
                <FieldWrap label="Support Period" span={2}><Input value={form.support_period} onChange={(e) => setForm({ ...form, support_period: e.target.value })} placeholder="e.g. 24/7 email + phone" /></FieldWrap>
              </>
            )}
            <DialogFooter className="col-span-2 mt-2">
              <Button type="button" variant="outline" onClick={() => setDlgOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={busy} data-testid="product-form-submit">{busy ? "Saving..." : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Categories dialog */}
      <Dialog open={catDlgOpen} onOpenChange={setCatDlgOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader><DialogTitle className="font-display">Product Categories</DialogTitle></DialogHeader>
          <div className="flex gap-2">
            <Input value={newCatName} onChange={(e) => setNewCatName(e.target.value)} placeholder="e.g. Networking" />
            <Button onClick={addCategory}>Add</Button>
          </div>
          <div className="border border-border divide-y divide-border max-h-64 overflow-y-auto">
            {cats.length === 0 ? (
              <div className="p-4 text-sm text-muted-foreground">No categories yet.</div>
            ) : cats.map((c) => (
              <div key={c.id} className="flex items-center justify-between px-3 py-2 text-sm">
                <span>{c.name}</span>
                {isAdmin && (
                  <Button variant="ghost" size="icon" className="text-destructive" onClick={async () => {
                    try { await api.delete(`/products/categories/${c.id}`); loadCats(); toast.success("Removed"); }
                    catch (e) { toast.error(formatApiError(e)); }
                  }}>
                    <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete product?</AlertDialogTitle>
            <AlertDialogDescription>Permanently delete <b>{toDelete?.name}</b>?</AlertDialogDescription>
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

function FieldWrap({ label, hint, required, span = 1, children }) {
  return (
    <div className={`space-y-1.5 ${span === 2 ? "col-span-2" : ""}`}>
      <Label className="text-xs uppercase tracking-widest">
        {label}
        {required && <span className="text-destructive ml-0.5">*</span>}
        {hint && <span className="ml-2 normal-case tracking-normal text-[10px] text-muted-foreground">({hint})</span>}
      </Label>
      {children}
    </div>
  );
}
