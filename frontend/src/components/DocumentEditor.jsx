/**
 * Shared editor for Quotations and Invoices.
 * Handles header (customer, date, currency), items table, footer notes, status transitions.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Plus, Trash2, Download, Save, Send } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import StatusBadge from "@/components/StatusBadge";
import { fmtMoney, todayInput } from "@/lib/format";

const CURRENCIES = ["IDR", "USD", "EUR", "SGD", "MYR", "AUD"];

const emptyItem = () => ({ product_id: "", product_name: "", description: "", quantity: 1, unit_price: 0, discount_percent: 0, tax_percent: 11 });

function computeTotals(items) {
  let subtotal = 0, discount = 0, tax = 0, total = 0;
  for (const it of items || []) {
    const qty = Number(it.quantity || 0);
    const up = Number(it.unit_price || 0);
    const d = Number(it.discount_percent || 0);
    const t = Number(it.tax_percent || 0);
    const s = qty * up;
    const dAmt = (s * d) / 100;
    const after = s - dAmt;
    const tAmt = (after * t) / 100;
    subtotal += s; discount += dAmt; tax += tAmt; total += after + tAmt;
  }
  return { subtotal, discount, tax, total };
}

export default function DocumentEditor({ kind }) {
  const isQuotation = kind === "quotation";
  const listPath = isQuotation ? "/quotations" : "/invoices";
  const apiBase = isQuotation ? "/quotations" : "/invoices";
  const { id } = useParams();
  const isNew = !id;
  const navigate = useNavigate();

  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [settings, setSettings] = useState({});
  const [doc, setDoc] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/customers/all").then((r) => setCustomers(r.data));
    api.get("/products/all").then((r) => setProducts(r.data));
    api.get("/settings").then((r) => setSettings(r.data));
  }, []);

  useEffect(() => {
    if (isNew) {
      const defaults = {
        customer_id: "",
        date: todayInput(),
        currency: "IDR",
        items: [emptyItem()],
        notes: "",
        payment_terms: "50% down payment, 50% on delivery",
      };
      if (isQuotation) {
        defaults.valid_until = "";
        defaults.delivery_time = "";
        defaults.status = "draft";
      } else {
        defaults.due_date = "";
        defaults.status = "unpaid";
        defaults.paid_amount = 0;
        defaults.quotation_id = "";
      }
      setDoc(defaults);
    } else {
      api.get(`${apiBase}/${id}`).then((r) => setDoc(r.data));
    }
  }, [id, isNew, apiBase, isQuotation]);

  const totals = useMemo(() => computeTotals(doc?.items || []), [doc]);

  if (!doc) return <div className="text-sm text-muted-foreground">Loading…</div>;

  const setField = (k, v) => setDoc((d) => ({ ...d, [k]: v }));
  const setItem = (i, patch) => setDoc((d) => {
    const items = [...d.items];
    items[i] = { ...items[i], ...patch };
    return { ...d, items };
  });
  const addItem = () => setDoc((d) => ({ ...d, items: [...d.items, emptyItem()] }));
  const removeItem = (i) => setDoc((d) => ({ ...d, items: d.items.filter((_, idx) => idx !== i) }));

  const applyProduct = (i, pid) => {
    const p = products.find((x) => x.id === pid);
    if (!p) return setItem(i, { product_id: "" });
    setItem(i, {
      product_id: p.id,
      product_name: p.name,
      description: p.description || "",
      unit_price: p.selling_price || 0,
      tax_percent: p.tax_percent || 0,
    });
  };

  const save = async (nextStatus) => {
    if (!doc.customer_id) return toast.error("Select a customer");
    if (!doc.items?.length) return toast.error("Add at least one line item");
    for (const it of doc.items) if (!it.product_name) return toast.error("Every line needs a product / name");

    setBusy(true);
    try {
      const payload = { ...doc };
      if (nextStatus) payload.status = nextStatus;
      payload.items = payload.items.map((it) => ({
        product_id: it.product_id || "",
        product_name: it.product_name,
        description: it.description || "",
        quantity: Number(it.quantity || 0),
        unit_price: Number(it.unit_price || 0),
        discount_percent: Number(it.discount_percent || 0),
        tax_percent: Number(it.tax_percent || 0),
      }));

      let result;
      if (isNew) {
        const { data } = await api.post(apiBase, payload);
        result = data;
        toast.success(`${isQuotation ? "Quotation" : "Invoice"} ${data.number} created`);
        navigate(`${listPath}/${data.id}`, { replace: true });
      } else {
        const { data } = await api.put(`${apiBase}/${id}`, payload);
        result = data;
        toast.success("Saved");
        setDoc((prev) => ({ ...prev, ...data }));
      }
      return result;
    } catch (err) {
      toast.error(formatApiError(err));
    } finally { setBusy(false); }
  };

  const changeStatus = async (status) => {
    try {
      await api.post(`${apiBase}/${id}/status`, null, { params: { status } });
      toast.success(`Status → ${status}`);
      setDoc((d) => ({ ...d, status }));
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const downloadPdf = async () => {
    if (isNew) return toast.error("Save first");
    try {
      const res = await api.get(`${apiBase}/${id}/pdf`, { responseType: "blob" });
      const u = window.URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = u; a.download = `${doc.number}.pdf`; a.click();
      window.URL.revokeObjectURL(u);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const currency = doc.currency || "IDR";

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <Link to={listPath} className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" strokeWidth={1.5} /> Back to {isQuotation ? "Quotations" : "Invoices"}
        </Link>
        <div className="flex items-center gap-2">
          {!isNew && <StatusBadge status={doc.status} />}
        </div>
      </div>

      <div className="border-b border-border pb-6 mb-6">
        <div className="label-eyebrow mb-2">{isQuotation ? "Quotation" : "Invoice"}</div>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h1 className="text-3xl sm:text-4xl font-display font-semibold tracking-tight font-mono">
            {isNew ? "New" : doc.number}
          </h1>
          <div className="flex flex-wrap gap-2">
            {!isNew && (
              <Button variant="outline" size="sm" onClick={downloadPdf}>
                <Download className="h-4 w-4 mr-2" strokeWidth={1.5} /> PDF
              </Button>
            )}
            <Button size="sm" onClick={() => save()} disabled={busy} data-testid="doc-save-button">
              <Save className="h-4 w-4 mr-2" strokeWidth={1.5} />
              {busy ? "Saving…" : "Save"}
            </Button>
            {!isNew && isQuotation && doc.status === "draft" && (
              <Button size="sm" variant="outline" onClick={() => changeStatus("sent")}>
                <Send className="h-4 w-4 mr-2" strokeWidth={1.5} /> Mark as Sent
              </Button>
            )}
            {!isNew && isQuotation && doc.status !== "approved" && doc.status !== "rejected" && (
              <>
                <Button size="sm" variant="outline" onClick={() => changeStatus("approved")}>Approve</Button>
                <Button size="sm" variant="outline" className="text-destructive" onClick={() => changeStatus("rejected")}>Reject</Button>
              </>
            )}
            {!isNew && !isQuotation && (
              <Select value={doc.status} onValueChange={(v) => changeStatus(v)}>
                <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["draft","unpaid","partial","paid","cancelled"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>
      </div>

      {/* Header form */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
        <div className="space-y-1.5 md:col-span-2">
          <Label className="text-xs uppercase tracking-widest">Customer *</Label>
          <Select value={doc.customer_id || ""} onValueChange={(v) => setField("customer_id", v)}>
            <SelectTrigger data-testid="doc-customer-select"><SelectValue placeholder="Select customer" /></SelectTrigger>
            <SelectContent>
              {customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name} ({c.code})</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs uppercase tracking-widest">Date *</Label>
          <Input type="date" value={doc.date || ""} onChange={(e) => setField("date", e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs uppercase tracking-widest">{isQuotation ? "Valid Until" : "Due Date"}</Label>
          <Input type="date" value={isQuotation ? (doc.valid_until || "") : (doc.due_date || "")}
            onChange={(e) => setField(isQuotation ? "valid_until" : "due_date", e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs uppercase tracking-widest">Currency</Label>
          <Select value={doc.currency || "IDR"} onValueChange={(v) => setField("currency", v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{CURRENCIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>

      {/* Line items */}
      <div className="border border-border bg-card mb-6">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <div className="font-display font-medium">Line Items</div>
          <Button size="sm" variant="outline" onClick={addItem} data-testid="doc-add-item">
            <Plus className="h-4 w-4 mr-2" strokeWidth={1.5} /> Add item
          </Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left label-eyebrow border-b border-border">
                <th className="px-3 py-2 w-8">#</th>
                <th className="px-3 py-2 w-64">Product</th>
                <th className="px-3 py-2">Description</th>
                <th className="px-3 py-2 w-20 text-right">Qty</th>
                <th className="px-3 py-2 w-32 text-right">Unit Price</th>
                <th className="px-3 py-2 w-20 text-right">Disc %</th>
                <th className="px-3 py-2 w-20 text-right">Tax %</th>
                <th className="px-3 py-2 w-36 text-right">Total</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {(doc.items || []).map((it, i) => {
                const s = Number(it.quantity || 0) * Number(it.unit_price || 0);
                const dAmt = (s * Number(it.discount_percent || 0)) / 100;
                const after = s - dAmt;
                const line = after + (after * Number(it.tax_percent || 0)) / 100;
                return (
                  <tr key={i} className="border-b border-border">
                    <td className="px-3 py-2 text-muted-foreground">{i + 1}</td>
                    <td className="px-3 py-2">
                      <div className="space-y-1">
                        <Select value={it.product_id || "__custom"} onValueChange={(v) => v === "__custom" ? setItem(i, { product_id: "" }) : applyProduct(i, v)}>
                          <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Custom line" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="__custom">Custom line</SelectItem>
                            {products.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <Input className="h-8 text-xs" value={it.product_name} onChange={(e) => setItem(i, { product_name: e.target.value })} placeholder="Product / description name" />
                      </div>
                    </td>
                    <td className="px-3 py-2"><Textarea className="min-h-[36px] text-xs" rows={1} value={it.description || ""} onChange={(e) => setItem(i, { description: e.target.value })} /></td>
                    <td className="px-3 py-2"><Input type="number" step="0.01" className="h-8 text-right text-xs" value={it.quantity} onChange={(e) => setItem(i, { quantity: e.target.value })} /></td>
                    <td className="px-3 py-2"><Input type="number" step="0.01" className="h-8 text-right text-xs" value={it.unit_price} onChange={(e) => setItem(i, { unit_price: e.target.value })} /></td>
                    <td className="px-3 py-2"><Input type="number" step="0.01" className="h-8 text-right text-xs" value={it.discount_percent} onChange={(e) => setItem(i, { discount_percent: e.target.value })} /></td>
                    <td className="px-3 py-2"><Input type="number" step="0.01" className="h-8 text-right text-xs" value={it.tax_percent} onChange={(e) => setItem(i, { tax_percent: e.target.value })} /></td>
                    <td className="px-3 py-2 text-right tabular-nums font-medium">{fmtMoney(line, currency)}</td>
                    <td className="px-1">
                      <Button variant="ghost" size="icon" onClick={() => removeItem(i)} className="text-destructive"><Trash2 className="h-4 w-4" strokeWidth={1.5} /></Button>
                    </td>
                  </tr>
                );
              })}
              {(!doc.items || doc.items.length === 0) && (
                <tr><td colSpan={9} className="text-center text-sm text-muted-foreground py-6">No items — click "Add item".</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Totals + footer notes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs uppercase tracking-widest">Notes</Label>
            <Textarea value={doc.notes || ""} onChange={(e) => setField("notes", e.target.value)} rows={3} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-widest">Payment Terms</Label>
              <Input value={doc.payment_terms || ""} onChange={(e) => setField("payment_terms", e.target.value)} />
            </div>
            {isQuotation && (
              <div className="space-y-1.5">
                <Label className="text-xs uppercase tracking-widest">Delivery Time</Label>
                <Input value={doc.delivery_time || ""} onChange={(e) => setField("delivery_time", e.target.value)} />
              </div>
            )}
          </div>
        </div>

        <div className="border border-border bg-card p-5 space-y-2 h-fit">
          <div className="label-eyebrow mb-3">Summary</div>
          <Row k="Subtotal" v={fmtMoney(totals.subtotal, currency)} />
          <Row k="Discount" v={"- " + fmtMoney(totals.discount, currency)} />
          <Row k="Tax" v={fmtMoney(totals.tax, currency)} />
          <div className="border-t border-border pt-2 mt-2">
            <Row k="Total" v={fmtMoney(totals.total, currency)} big />
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ k, v, big }) {
  return (
    <div className="flex items-center justify-between">
      <div className={big ? "font-display font-medium" : "text-sm text-muted-foreground"}>{k}</div>
      <div className={`tabular-nums ${big ? "font-display text-xl font-semibold" : "text-sm font-medium"}`}>{v}</div>
    </div>
  );
}
