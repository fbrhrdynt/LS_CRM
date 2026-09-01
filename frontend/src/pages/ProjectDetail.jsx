import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, KeyRound, Package, BadgeCheck } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import StatusBadge from "@/components/StatusBadge";
import { fmtDate } from "@/lib/format";

export default function ProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [linkKind, setLinkKind] = useState(null); // 'accounts' | 'products' | 'licenses'
  const [available, setAvailable] = useState([]);
  const [picked, setPicked] = useState(new Set());
  const [busy, setBusy] = useState(false);

  const load = () => api.get(`/projects/${id}`).then((r) => setProject(r.data));
  useEffect(() => { load(); }, [id]);

  const openLink = async (kind) => {
    setLinkKind(kind);
    const endpoint = kind === "accounts" ? "/accounts?per_page=1000" : kind === "products" ? "/products/all" : "/licenses?per_page=1000";
    const { data } = await api.get(endpoint);
    const items = data.items || data;
    setAvailable(items);
    setPicked(new Set(project?.[`${kind === "products" ? "product" : kind.slice(0, -1)}_ids`] || project?.[`${kind.replace(/s$/, "")}_ids`] || project?.[`${kind === "accounts" ? "account_ids" : kind === "licenses" ? "license_ids" : "product_ids"}`] || []));
  };

  const savePicks = async () => {
    setBusy(true);
    try {
      const field = linkKind === "accounts" ? "account_ids" : linkKind === "products" ? "product_ids" : "license_ids";
      await api.put(`/projects/${id}`, { [field]: Array.from(picked) });
      toast.success("Linked");
      setLinkKind(null);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  if (!project) return <div className="text-sm text-muted-foreground">Loading…</div>;

  return (
    <div>
      <Link to="/projects" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 mb-4">
        <ArrowLeft className="h-4 w-4" strokeWidth={1.5} /> Back to Projects
      </Link>

      <div className="border-b border-border pb-6 mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="label-eyebrow mb-2 font-mono">{project.number}</div>
          <h1 className="text-3xl font-display font-semibold tracking-tight">{project.name}</h1>
          <div className="text-sm text-muted-foreground mt-1">{project.customer?.company_name}</div>
        </div>
        <div className="text-right space-y-1">
          <StatusBadge status={project.status} />
          <div className="text-xs text-muted-foreground">{fmtDate(project.start_date)} → {fmtDate(project.end_date)}</div>
        </div>
      </div>

      {project.description && (
        <div className="border border-border bg-card p-5 mb-6">
          <div className="label-eyebrow mb-2">Description</div>
          <div className="text-sm leading-relaxed whitespace-pre-line">{project.description}</div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <LinkedCard
          title="Products" icon={Package} items={project.products || []} onLink={() => openLink("products")}
          empty="No products linked" renderer={(p) => (
            <div key={p.id} className="px-4 py-2 hover-row flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{p.name}</div>
                <div className="text-xs text-muted-foreground font-mono">{p.code}</div>
              </div>
              <span className="label-eyebrow">{p.product_type}</span>
            </div>
          )}
        />
        <LinkedCard
          title="Accounts" icon={KeyRound} items={project.accounts || []} onLink={() => openLink("accounts")}
          empty="No accounts linked" renderer={(a) => (
            <div key={a.id} className="px-4 py-2 hover-row">
              <div className="text-sm font-medium">{a.name}</div>
              <div className="text-xs text-muted-foreground">{a.category} · {a.email || a.username}</div>
            </div>
          )}
        />
        <LinkedCard
          title="Licenses" icon={BadgeCheck} items={project.licenses || []} onLink={() => openLink("licenses")}
          empty="No licenses linked" renderer={(l) => (
            <div key={l.id} className="px-4 py-2 hover-row">
              <div className="text-sm font-medium">{l.product_name || l.license_code}</div>
              <div className="text-xs text-muted-foreground font-mono">Expires {fmtDate(l.expiry_date)}</div>
            </div>
          )}
        />
      </div>

      <Dialog open={!!linkKind} onOpenChange={(o) => !o && setLinkKind(null)}>
        <DialogContent className="sm:max-w-[520px] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-display capitalize">Link {linkKind}</DialogTitle>
          </DialogHeader>
          <div className="space-y-1 max-h-96 overflow-y-auto border border-border rounded-sm">
            {available.length === 0 ? (
              <div className="p-4 text-sm text-muted-foreground">No items available.</div>
            ) : available.map((it) => {
              const checked = picked.has(it.id);
              return (
                <label key={it.id} className="flex items-start gap-3 px-4 py-2 hover-row cursor-pointer">
                  <Checkbox checked={checked} onCheckedChange={(v) => {
                    const next = new Set(picked);
                    if (v) next.add(it.id); else next.delete(it.id);
                    setPicked(next);
                  }} />
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{it.name || it.product_name || it.license_code}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {it.category || it.code || it.registration_number || ""}
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLinkKind(null)}>Cancel</Button>
            <Button onClick={savePicks} disabled={busy}>{busy ? "Saving..." : "Save links"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function LinkedCard({ title, icon: Icon, items, empty, onLink, renderer }) {
  return (
    <div className="border border-border bg-card">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="font-display font-medium flex items-center gap-2"><Icon className="h-4 w-4" strokeWidth={1.5} /> {title}</div>
        <Button size="sm" variant="outline" onClick={onLink}>Manage</Button>
      </div>
      <div className="divide-y divide-border max-h-72 overflow-y-auto">
        {items.length === 0 ? (
          <div className="px-4 py-6 text-sm text-muted-foreground">{empty}</div>
        ) : items.map(renderer)}
      </div>
    </div>
  );
}
