import { useEffect, useState } from "react";
import { Search, History } from "lucide-react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { fmtDateTime } from "@/lib/format";

const MODULES = ["auth", "customers", "products", "quotations", "invoices", "projects", "accounts", "licenses", "users", "settings"];

export default function ActivityLogs() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [module, setModule] = useState("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const load = async () => {
    const params = { q, page, per_page: 30 };
    if (module !== "all") params.module = module;
    const { data } = await api.get("/activity-logs", { params });
    setRows(data.items); setTotalPages(data.total_pages);
  };
  useEffect(() => { load(); }, [q, module, page]); // eslint-disable-line

  return (
    <div>
      <PageHeader eyebrow="Admin" title="Activity Logs" description="Every login, create, update, delete, and credential reveal — with timestamp and user." />

      <div className="border border-border bg-card">
        <div className="p-3 border-b border-border flex flex-col md:flex-row gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
            <Input placeholder="Search user, action, details…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} className="pl-8" />
          </div>
          <Select value={module} onValueChange={(v) => { setPage(1); setModule(v); }}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All modules</SelectItem>
              {MODULES.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        {rows.length === 0 ? (
          <EmptyState icon={History} title="No activity" />
        ) : (
          <div className="divide-y divide-border">
            {rows.map((a) => (
              <div key={a.id} className="px-5 py-3 flex items-start gap-4 hover-row">
                <div className="w-24 shrink-0 label-eyebrow">{a.module}</div>
                <div className="w-32 shrink-0">
                  <span className="text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 border rounded-sm bg-muted text-muted-foreground border-border">
                    {a.action}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm truncate">
                    <span className="font-medium">{a.user_name || a.user_email || "system"}</span>
                    <span className="text-muted-foreground"> · {a.details}</span>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground shrink-0">{fmtDateTime(a.timestamp)}</div>
              </div>
            ))}
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
    </div>
  );
}
