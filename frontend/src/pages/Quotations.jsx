import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Plus, Search, Pencil, Trash2, FileText as FileIcon, Download } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/contexts/AuthContext";
import { fmtDate, fmtMoney } from "@/lib/format";

export default function Quotations() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [toDelete, setToDelete] = useState(null);

  const load = async () => {
    const params = { q, page, per_page: 20 };
    if (status !== "all") params.status = status;
    const { data } = await api.get("/quotations", { params });
    setRows(data.items);
    setTotalPages(data.total_pages);
  };
  useEffect(() => { load(); }, [q, status, page]); // eslint-disable-line

  const download = async (id, number) => {
    try {
      const res = await api.get(`/quotations/${id}/pdf`, { responseType: "blob" });
      const u = window.URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = u; a.download = `${number}.pdf`; a.click();
      window.URL.revokeObjectURL(u);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const convertToInvoice = async (qid, number) => {
    try {
      const { data } = await api.post(`/invoices/from-quotation/${qid}`);
      toast.success(`Invoice ${data.number} created from ${number}`);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const doDelete = async () => {
    try {
      await api.delete(`/quotations/${toDelete.id}`);
      toast.success("Deleted");
      setToDelete(null);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Sales"
        title="Quotations"
        description="Track every proposal from draft to approval — with automatic numbering (QTN-YYYY-00001) and PDF export."
        actions={
          <Button size="sm" asChild data-testid="quotation-new-button">
            <Link to="/quotations/new"><Plus className="h-4 w-4 mr-2" strokeWidth={1.5} />New quotation</Link>
          </Button>
        }
      />

      <div className="border border-border bg-card">
        <div className="p-3 border-b border-border flex flex-col md:flex-row items-stretch md:items-center gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
            <Input placeholder="Search number…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} className="pl-8" />
          </div>
          <Select value={status} onValueChange={(v) => { setPage(1); setStatus(v); }}>
            <SelectTrigger className="w-40"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="sent">Sent</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {rows.length === 0 ? (
          <EmptyState icon={FileIcon} title="No quotations yet" description="Draft your first quotation to your customer." action={<Button asChild size="sm"><Link to="/quotations/new"><Plus className="h-4 w-4 mr-2" />New quotation</Link></Button>} />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-40">Number</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead className="w-32">Date</TableHead>
                  <TableHead className="w-32">Valid Until</TableHead>
                  <TableHead className="text-right w-40">Total</TableHead>
                  <TableHead className="w-32">Status</TableHead>
                  <TableHead className="text-right w-32">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id} className="hover-row">
                    <TableCell className="font-mono text-xs">
                      <Link to={`/quotations/${r.id}`} className="hover:text-primary hover:underline">{r.number}</Link>
                    </TableCell>
                    <TableCell className="font-medium">{r.customer_name || "—"}</TableCell>
                    <TableCell className="text-xs">{fmtDate(r.date)}</TableCell>
                    <TableCell className="text-xs">{fmtDate(r.valid_until)}</TableCell>
                    <TableCell className="text-right tabular-nums font-medium">{fmtMoney(r.totals?.total, r.currency)}</TableCell>
                    <TableCell><StatusBadge status={r.status} /></TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" title="PDF" onClick={() => download(r.id, r.number)}><Download className="h-4 w-4" strokeWidth={1.5} /></Button>
                      <Button variant="ghost" size="icon" asChild title="Edit"><Link to={`/quotations/${r.id}`}><Pencil className="h-4 w-4" strokeWidth={1.5} /></Link></Button>
                      {r.status === "approved" && (
                        <Button variant="ghost" size="sm" onClick={() => convertToInvoice(r.id, r.number)} className="text-xs">→ Invoice</Button>
                      )}
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

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete quotation?</AlertDialogTitle>
            <AlertDialogDescription>Delete <b>{toDelete?.number}</b>?</AlertDialogDescription>
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
