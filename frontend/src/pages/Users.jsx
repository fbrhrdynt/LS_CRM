import { useEffect, useState } from "react";
import { toast } from "sonner";
import { KeyRound, Pencil, Plus, Trash2, UserCog } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { useAuth } from "@/contexts/AuthContext";
import { fmtDate } from "@/lib/format";

const EMPTY = { name: "", email: "", role: "staff", password: "", permissions: [] };

export default function Users() {
  const { user: me } = useAuth();
  const [rows, setRows] = useState([]);
  const [permissionOptions, setPermissionOptions] = useState([]);
  const [dlgOpen, setDlgOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [resetUser, setResetUser] = useState(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetConfirm, setResetConfirm] = useState("");
  const [resetBusy, setResetBusy] = useState(false);

  const load = async () => {
    const [u, p] = await Promise.all([api.get("/users"), api.get("/users/permissions")]);
    setRows(u.data.items);
    setPermissionOptions(p.data);
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setForm({ ...EMPTY, permissions: [] }); setEditingId(null); setDlgOpen(true); };
  const openEdit = (r) => { setForm({ name:r.name||"", email:r.email||"", role:r.role||"staff", password:"", permissions:[...(r.permissions||[])] }); setEditingId(r.id); setDlgOpen(true); };
  const togglePermission = (key) => setForm((cur) => ({ ...cur, permissions: cur.permissions.includes(key) ? cur.permissions.filter((p)=>p!==key) : [...cur.permissions,key] }));

  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      const payload = { name:form.name, email:form.email, role:form.role, permissions: form.role === "admin" ? permissionOptions.map((p)=>p.key) : form.permissions };
      if (editingId) { await api.put(`/users/${editingId}`, payload); toast.success("User updated"); }
      else { await api.post("/users", { ...payload, password:form.password }); toast.success("User created"); }
      setDlgOpen(false); await load();
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const doDelete = async () => { try { await api.delete(`/users/${toDelete.id}`); toast.success("User deleted"); setToDelete(null); await load(); } catch(e){ toast.error(formatApiError(e)); } };
  const openReset = (r) => { setResetUser(r); setResetPassword(""); setResetConfirm(""); };
  const doResetPassword = async (e) => {
    e.preventDefault();
    if (resetPassword !== resetConfirm) return toast.error("Password confirmation does not match");
    setResetBusy(true);
    try { await api.post(`/users/${resetUser.id}/reset-password`, { new_password:resetPassword }); toast.success("Password reset. User sessions signed out."); setResetUser(null); }
    catch(err){ toast.error(formatApiError(err)); } finally { setResetBusy(false); }
  };
  const accessText = (r) => r.role === "admin" ? "All access" : (!r.permissions?.length ? "Dashboard only" : r.permissions.map((key)=>permissionOptions.find((p)=>p.key===key)?.label||key).join(", "));

  return <div>
    <PageHeader eyebrow="Admin" title="User Management" description="Create users, choose module access, and reset passwords." actions={<Button size="sm" onClick={openNew}><Plus className="h-4 w-4 mr-2" />New user</Button>} />
    <div className="border border-border bg-card">
      {rows.length===0 ? <EmptyState icon={UserCog} title="No users" action={<Button onClick={openNew} size="sm">New user</Button>} /> :
      <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Email</TableHead><TableHead>Role</TableHead><TableHead>Access</TableHead><TableHead>Created</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader><TableBody>
        {rows.map((r)=><TableRow key={r.id}><TableCell className="font-medium">{r.name}</TableCell><TableCell className="font-mono text-xs">{r.email}</TableCell><TableCell>{r.role}</TableCell><TableCell className="text-xs max-w-md"><div className="truncate" title={accessText(r)}>{accessText(r)}</div></TableCell><TableCell className="text-xs text-muted-foreground">{fmtDate(r.created_at)}</TableCell><TableCell className="text-right whitespace-nowrap">
          {r.id!==me?.id && <Button variant="ghost" size="icon" title="Reset password" onClick={()=>openReset(r)}><KeyRound className="h-4 w-4" /></Button>}
          <Button variant="ghost" size="icon" title="Edit user" onClick={()=>openEdit(r)}><Pencil className="h-4 w-4" /></Button>
          {r.id!==me?.id && <Button variant="ghost" size="icon" className="text-destructive" onClick={()=>setToDelete(r)}><Trash2 className="h-4 w-4" /></Button>}
        </TableCell></TableRow>)}
      </TableBody></Table></div>}
    </div>

    <Dialog open={dlgOpen} onOpenChange={setDlgOpen}><DialogContent className="sm:max-w-[620px] max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>{editingId?"Edit User":"New User"}</DialogTitle></DialogHeader><form onSubmit={submit} className="space-y-4">
      <div><Label>Name *</Label><Input required value={form.name} onChange={(e)=>setForm({...form,name:e.target.value})}/></div>
      <div><Label>Email *</Label><Input required type="email" value={form.email} onChange={(e)=>setForm({...form,email:e.target.value})}/></div>
      <div><Label>Role</Label><Select value={form.role} onValueChange={(v)=>setForm({...form,role:v})}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="admin">Administrator</SelectItem><SelectItem value="staff">Staff</SelectItem></SelectContent></Select>{form.role==="admin" && <div className="text-xs text-muted-foreground mt-1">Administrator always has full access.</div>}</div>
      {!editingId && <div><Label>Initial Password *</Label><Input type="password" minLength={12} maxLength={128} required value={form.password} onChange={(e)=>setForm({...form,password:e.target.value})}/><div className="text-xs text-muted-foreground mt-1">Minimum 12 characters.</div></div>}
      {form.role==="staff" && <div className="space-y-2"><div className="flex items-center justify-between"><Label>Module Access</Label><div className="flex gap-2"><button type="button" className="text-xs text-primary hover:underline" onClick={()=>setForm({...form,permissions:permissionOptions.map((p)=>p.key)})}>Select all</button><button type="button" className="text-xs text-muted-foreground hover:underline" onClick={()=>setForm({...form,permissions:[]})}>Clear</button></div></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-2 border border-border p-3">{permissionOptions.map((item)=><label key={item.key} className="flex items-center gap-2 text-sm cursor-pointer p-2 hover:bg-muted"><input type="checkbox" checked={form.permissions.includes(item.key)} onChange={()=>togglePermission(item.key)} className="h-4 w-4"/><span>{item.label}</span></label>)}</div><div className="text-xs text-muted-foreground">Dashboard & Change Password always available. Delete operations remain Administrator-only.</div></div>}
      <DialogFooter><Button type="button" variant="outline" onClick={()=>setDlgOpen(false)}>Cancel</Button><Button type="submit" disabled={busy}>{busy?"Saving...":"Save"}</Button></DialogFooter>
    </form></DialogContent></Dialog>

    <Dialog open={!!resetUser} onOpenChange={(o)=>!o&&setResetUser(null)}><DialogContent className="sm:max-w-[440px]"><DialogHeader><DialogTitle>Reset Password</DialogTitle></DialogHeader><form onSubmit={doResetPassword} className="space-y-4"><div className="text-sm text-muted-foreground">Reset password for <b className="text-foreground">{resetUser?.email}</b>. All active sessions will be signed out.</div><div><Label>New Password</Label><Input type="password" required minLength={12} maxLength={128} value={resetPassword} onChange={(e)=>setResetPassword(e.target.value)}/></div><div><Label>Confirm New Password</Label><Input type="password" required minLength={12} maxLength={128} value={resetConfirm} onChange={(e)=>setResetConfirm(e.target.value)}/></div><DialogFooter><Button type="button" variant="outline" onClick={()=>setResetUser(null)}>Cancel</Button><Button type="submit" disabled={resetBusy}>{resetBusy?"Resetting...":"Reset Password"}</Button></DialogFooter></form></DialogContent></Dialog>

    <AlertDialog open={!!toDelete} onOpenChange={(o)=>!o&&setToDelete(null)}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Delete user?</AlertDialogTitle><AlertDialogDescription>Delete <b>{toDelete?.email}</b>?</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={doDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Delete</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
  </div>;
}
