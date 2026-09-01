import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Plus, Search, Pencil, Trash2, FolderKanban } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
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
import { useAuth } from "@/contexts/AuthContext";
import { fmtDate } from "@/lib/format";

const STATUSES = ["planning", "progress", "completed", "maintenance", "closed"];
const EMPTY = {
  name: "", customer_id: "", start_date: "", end_date: "", description: "",
  status: "planning", product_ids: [], account_ids: [], license_ids: [],
};

export default function Projects() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [dlgOpen, setDlgOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);

  const load = async () => {
    const params = { q, page, per_page: 20 };
    if (status !== "all") params.status = status;
    const { data } = await api.get("/projects", { params });
    setRows(data.items); setTotalPages(data.total_pages);
  };
  useEffect(() => { load(); }, [q, status, page]); // eslint-disable-line
  useEffect(() => { api.get("/customers/all").then((r) => setCustomers(r.data)); }, []);

  const openNew = () => { setForm(EMPTY); setEditingId(null); setDlgOpen(true); };
  const openEdit = (r) => { setForm({ ...EMPTY, ...r }); setEditingId(r.id); setDlgOpen(true); };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (editingId) { await api.put(`/projects/${editingId}`, form); toast.success("Project updated"); }
      else { await api.post("/projects", form); toast.success("Project created"); }
      setDlgOpen(false); load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const doDelete = async () => {
    try { await api.delete(`/projects/${toDelete.id}`); toast.success("Deleted"); setToDelete(null); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Operations"
        title="Projects"
        description="Track every engagement across its lifecycle — with linked products, accounts and licenses."
        actions={<Button size="sm" onClick={openNew} data-testid="project-new-button"><Plus className="h-4 w-4 mr-2" strokeWidth={1.5} />New project</Button>}
      />

      <div className="border border-border bg-card">
        <div className="p-3 border-b border-border flex flex-col md:flex-row gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
            <Input placeholder="Search project name or number…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} className="pl-8" />
          </div>
          <Select value={status} onValueChange={(v) => { setPage(1); setStatus(v); }}>
            <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        {rows.length === 0 ? (
          <EmptyState icon={FolderKanban} title="No projects yet" description="Create a project to link customers, products, and credentials together."
            action={<Button size="sm" onClick={openNew}><Plus className="h-4 w-4 mr-2" />New project</Button>} />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-40">Number</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead className="w-28">Start</TableHead>
                  <TableHead className="w-28">End</TableHead>
                  <TableHead className="w-28">Status</TableHead>
                  <TableHead className="text-right w-24">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id} className="hover-row">
                    <TableCell className="font-mono text-xs"><Link to={`/projects/${r.id}`} className="hover:text-primary hover:underline">{r.number}</Link></TableCell>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell>{r.customer_name || "—"}</TableCell>
                    <TableCell className="text-xs">{fmtDate(r.start_date)}</TableCell>
                    <TableCell className="text-xs">{fmtDate(r.end_date)}</TableCell>
                    <TableCell><StatusBadge status={r.status} /></TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(r)}><Pencil className="h-4 w-4" strokeWidth={1.5} /></Button>
                      {isAdmin && <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setToDelete(r)}><Trash2 className="h-4 w-4" strokeWidth={1.5} /></Button>}
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
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader><DialogTitle className="font-display">{editingId ? "Edit Project" : "New Project"}</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="grid grid-cols-2 gap-3">
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Name *</Label>
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="project-form-name" />
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Customer *</Label>
              <Select value={form.customer_id} onValueChange={(v) => setForm({ ...form, customer_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select customer" /></SelectTrigger>
                <SelectContent>{customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Start Date</Label>
              <Input type="date" value={form.start_date || ""} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">End Date</Label>
              <Input type="date" value={form.end_date || ""} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Status</Label>
              <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Description</Label>
              <Textarea value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} />
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
            <AlertDialogTitle>Delete project?</AlertDialogTitle>
            <AlertDialogDescription>Delete <b>{toDelete?.name}</b>?</AlertDialogDescription>
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
