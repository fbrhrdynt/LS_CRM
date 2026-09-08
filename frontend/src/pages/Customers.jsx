import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search, Pencil, Trash2, Download, Upload, Users as UsersIcon } from "lucide-react";
import api, { API, formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Table, TableHeader, TableRow, TableHead, TableBody, TableCell,
} from "@/components/ui/table";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/contexts/AuthContext";
import { fmtDate } from "@/lib/format";

const EMPTY = {
  code: "", company_name: "", pic_name: "", position: "", phone: "",
  email: "", address: "", website: "", notes: "",
};

export default function Customers() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [dlgOpen, setDlgOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/customers", { params: { q, page, per_page: 20 } });
      setRows(data.items);
      setTotalPages(data.total_pages);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, [q, page]);

  const openNew = () => {
    setForm(EMPTY);
    setEditingId(null);
    setDlgOpen(true);
  };
  const openEdit = (row) => {
    setForm({ ...EMPTY, ...row });
    setEditingId(row.id);
    setDlgOpen(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (editingId) {
        await api.put(`/customers/${editingId}`, form);
        toast.success("Customer updated");
      } else {
        await api.post("/customers", form);
        toast.success("Customer created");
      }
      setDlgOpen(false);
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const doDelete = async () => {
    if (!toDelete) return;
    try {
      await api.delete(`/customers/${toDelete.id}`);
      toast.success("Customer deleted");
      setToDelete(null);
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const exportXlsx = async () => {
    try {
      const res = await api.get("/customers/export/xlsx", { responseType: "blob" });
      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "customers.xlsx";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const importXlsx = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${API}/customers/import/xlsx`, {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Import failed");
      toast.success(`Imported ${data.created}, skipped ${data.skipped}`);
      load();
    } catch (err) {
      toast.error(err.message || "Import failed");
    } finally {
      e.target.value = "";
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Sales"
        title="Customers"
        description="Every company you do business with — with their PICs and contact details."
        actions={
          <>
            <label className="cursor-pointer">
              <input type="file" accept=".xlsx" className="hidden" onChange={importXlsx} data-testid="customer-import-input" />
              <Button variant="outline" size="sm" asChild>
                <span><Upload className="h-4 w-4 mr-2" strokeWidth={1.5} />Import</span>
              </Button>
            </label>
            <Button variant="outline" size="sm" onClick={exportXlsx} data-testid="customer-export-button">
              <Download className="h-4 w-4 mr-2" strokeWidth={1.5} />Export
            </Button>
            <Button size="sm" onClick={openNew} data-testid="customer-new-button">
              <Plus className="h-4 w-4 mr-2" strokeWidth={1.5} />New customer
            </Button>
          </>
        }
      />

      <div className="border border-border bg-card">
        <div className="p-3 border-b border-border flex items-center gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
            <Input
              placeholder="Search company, PIC, email, phone…"
              value={q}
              onChange={(e) => { setPage(1); setQ(e.target.value); }}
              className="pl-8"
              data-testid="customer-search-input"
            />
          </div>
        </div>

        {rows.length === 0 && !loading ? (
          <EmptyState
            icon={UsersIcon}
            title="No customers yet"
            description="Create your first customer to start issuing quotations and invoices."
            action={<Button onClick={openNew} size="sm"><Plus className="h-4 w-4 mr-2" />New customer</Button>}
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-32">Code</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>PIC</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead className="w-32">Created</TableHead>
                  <TableHead className="w-24 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id} className="hover-row" data-testid={`customer-row-${r.id}`}>
                    <TableCell className="font-mono text-xs">{r.code}</TableCell>
                    <TableCell className="font-medium">{r.company_name}</TableCell>
                    <TableCell>{r.pic_name || "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{r.phone || "—"}</TableCell>
                    <TableCell className="text-xs">{r.email || "—"}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{fmtDate(r.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(r)} data-testid={`customer-edit-${r.id}`}>
                        <Pencil className="h-4 w-4" strokeWidth={1.5} />
                      </Button>
                      {isAdmin && (
                        <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setToDelete(r)} data-testid={`customer-delete-${r.id}`}>
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

      <Dialog open={dlgOpen} onOpenChange={setDlgOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-display">{editingId ? "Edit Customer" : "New Customer"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={submit} className="grid grid-cols-2 gap-3">
            <Field label="Customer Code" hint="auto if blank">
              <Input value={form.code || ""} onChange={(e) => setForm({ ...form, code: e.target.value })} data-testid="customer-form-code" />
            </Field>
            <Field label="Company Name" required>
              <Input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} data-testid="customer-form-company_name" />
            </Field>
            <Field label="PIC Name">
              <Input value={form.pic_name} onChange={(e) => setForm({ ...form, pic_name: e.target.value })} />
            </Field>
            <Field label="Position">
              <Input value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} />
            </Field>
            <Field label="Phone">
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </Field>
            <Field label="Email">
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Website" span={2}>
              <Input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
            </Field>
            <Field label="Address" span={2}>
              <Textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} rows={2} />
            </Field>
            <Field label="Notes" span={2}>
              <Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} />
            </Field>
            <DialogFooter className="col-span-2 mt-2">
              <Button type="button" variant="outline" onClick={() => setDlgOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={busy} data-testid="customer-form-submit">{busy ? "Saving..." : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete customer?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete <b>{toDelete?.company_name}</b>. This cannot be undone.
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

function Field({ label, hint, required, span = 1, children }) {
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
