import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, UserCog } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/contexts/AuthContext";
import { fmtDate } from "@/lib/format";

const EMPTY = { name: "", email: "", role: "staff", password: "" };

export default function Users() {
  const { user: me } = useAuth();
  const [rows, setRows] = useState([]);
  const [dlgOpen, setDlgOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);

  const load = async () => {
    const { data } = await api.get("/users");
    setRows(data.items);
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setForm(EMPTY); setEditingId(null); setDlgOpen(true); };
  const openEdit = (r) => { setForm({ ...EMPTY, ...r, password: "" }); setEditingId(r.id); setDlgOpen(true); };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (editingId) {
        const p = { name: form.name, email: form.email, role: form.role };
        if (form.password) p.password = form.password;
        await api.put(`/users/${editingId}`, p);
        toast.success("User updated");
      } else {
        await api.post("/users", form);
        toast.success("User created");
      }
      setDlgOpen(false); load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const doDelete = async () => {
    try { await api.delete(`/users/${toDelete.id}`); toast.success("Deleted"); setToDelete(null); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Admin"
        title="User Management"
        description="Manage team members with granular role-based access — Administrator or Staff."
        actions={<Button size="sm" onClick={openNew} data-testid="user-new-button"><Plus className="h-4 w-4 mr-2" strokeWidth={1.5} />New user</Button>}
      />

      <div className="border border-border bg-card">
        {rows.length === 0 ? (
          <EmptyState icon={UserCog} title="No users" action={<Button onClick={openNew} size="sm">New user</Button>} />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="w-32">Role</TableHead>
                <TableHead className="w-32">Created</TableHead>
                <TableHead className="text-right w-24">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id} className="hover-row">
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="font-mono text-xs">{r.email}</TableCell>
                  <TableCell>
                    <span className={`text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 border rounded-sm ${
                      r.role === "admin" ? "bg-primary/10 text-primary border-primary/30" : "bg-muted text-muted-foreground border-border"
                    }`}>{r.role}</span>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{fmtDate(r.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(r)}><Pencil className="h-4 w-4" strokeWidth={1.5} /></Button>
                    {r.id !== me?.id && (
                      <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setToDelete(r)}><Trash2 className="h-4 w-4" strokeWidth={1.5} /></Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={dlgOpen} onOpenChange={setDlgOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader><DialogTitle className="font-display">{editingId ? "Edit User" : "New User"}</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="space-y-3">
            <div className="space-y-1.5"><Label className="text-xs uppercase tracking-widest">Name *</Label><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="space-y-1.5"><Label className="text-xs uppercase tracking-widest">Email *</Label><Input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Role</Label>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Administrator</SelectItem>
                  <SelectItem value="staff">Staff</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">{editingId ? "Password (leave blank to keep)" : "Password *"}</Label>
              <Input type="password" minLength={editingId ? undefined : 6} required={!editingId} value={form.password || ""} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDlgOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={busy}>{busy ? "Saving..." : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete user?</AlertDialogTitle>
            <AlertDialogDescription>Delete <b>{toDelete?.email}</b>?</AlertDialogDescription>
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
