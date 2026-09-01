import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Users,
  Package,
  FileText,
  Receipt,
  FolderKanban,
  KeyRound,
  BadgeCheck,
  UserCog,
  AlertTriangle,
  TrendingUp,
  Activity,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import StatusBadge from "@/components/StatusBadge";
import { fmtMoney, fmtRelative, fmtDate } from "@/lib/format";
import { DASHBOARD } from "@/constants/testIds";

const KPI_DEFS = [
  { key: "customers", label: "Customers", icon: Users, to: "/customers" },
  { key: "products", label: "Products", icon: Package, to: "/products" },
  { key: "quotations", label: "Quotations", icon: FileText, to: "/quotations" },
  { key: "invoices", label: "Invoices", icon: Receipt, to: "/invoices" },
  { key: "projects", label: "Projects", icon: FolderKanban, to: "/projects" },
  { key: "accounts", label: "Accounts", icon: KeyRound, to: "/accounts" },
  { key: "licenses", label: "Licenses", icon: BadgeCheck, to: "/licenses" },
  { key: "users", label: "Users", icon: UserCog, to: "/users" },
];

function KpiCard({ item, value }) {
  const Icon = item.icon;
  return (
    <Link
      to={item.to}
      className="border border-border bg-card p-5 hover:bg-muted/40 transition-colors group flex flex-col justify-between min-h-[120px]"
      data-testid={DASHBOARD.kpiCard(item.key)}
    >
      <div className="flex items-start justify-between">
        <div className="label-eyebrow">{item.label}</div>
        <Icon className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" strokeWidth={1.5} />
      </div>
      <div className="font-display text-4xl font-semibold tabular-nums mt-4">{value ?? 0}</div>
    </Link>
  );
}

function AlertList({ title, items, empty, testId, renderer }) {
  return (
    <div className="border border-border bg-card" data-testid={testId}>
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <div className="font-display font-medium">{title}</div>
        <AlertTriangle className="h-4 w-4 text-[hsl(var(--warning))]" strokeWidth={1.5} />
      </div>
      <div className="divide-y divide-border max-h-72 overflow-y-auto">
        {items.length === 0 ? (
          <div className="px-5 py-6 text-sm text-muted-foreground">{empty}</div>
        ) : (
          items.map(renderer)
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/summary").then((r) => setData(r.data));
  }, []);

  if (!data) {
    return <div className="text-sm text-muted-foreground">Loading dashboard…</div>;
  }

  const counts = data.counts || {};
  const alerts = data.alerts || {};
  const charts = data.charts || {};

  return (
    <div data-testid={DASHBOARD.root}>
      <PageHeader
        eyebrow="Overview"
        title="Command Center"
        description="Real-time metrics across every LogiSource module — with actionable alerts on expiring assets and outstanding invoices."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {KPI_DEFS.map((k) => (
          <KpiCard key={k.key} item={k} value={counts[k.key]} />
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-8">
        <ChartCard title="Monthly Quotations" data={charts.monthly_quotations} type="bar" color="hsl(var(--chart-1))" />
        <ChartCard title="Monthly Invoices" data={charts.monthly_invoices} type="bar" color="hsl(var(--chart-2))" />
        <ChartCard title="Customer Growth" data={charts.monthly_customers} type="line" color="hsl(var(--chart-3))" />
      </div>

      {/* Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-8">
        <AlertList
          title="Licenses expiring soon"
          testId="dashboard-alert-licenses"
          items={alerts.licenses_30d || []}
          empty="No licenses expiring within 30 days"
          renderer={(l) => (
            <div key={l.id} className="px-5 py-3 flex items-center justify-between hover-row">
              <div className="min-w-0">
                <div className="font-medium truncate">{l.name || "—"}</div>
                <div className="text-xs text-muted-foreground">Expires {fmtDate(l.expiry_date)}</div>
              </div>
              <ExpiryPill days={l.days_left} />
            </div>
          )}
        />
        <AlertList
          title="Registrations expiring"
          testId="dashboard-alert-registrations"
          items={alerts.registrations_30d || []}
          empty="No registrations expiring within 30 days"
          renderer={(a) => (
            <div key={a.id} className="px-5 py-3 flex items-center justify-between hover-row">
              <div className="min-w-0">
                <div className="font-medium truncate">{a.name}</div>
                <div className="text-xs text-muted-foreground">{a.category} · Expires {fmtDate(a.expiry_date)}</div>
              </div>
              <ExpiryPill days={a.days_left} />
            </div>
          )}
        />
        <AlertList
          title="Unpaid invoices"
          testId="dashboard-alert-unpaid"
          items={alerts.unpaid_invoices || []}
          empty="All invoices are settled 🎉"
          renderer={(i) => (
            <Link
              key={i.id}
              to={`/invoices/${i.id}`}
              className="px-5 py-3 flex items-center justify-between hover-row"
            >
              <div className="min-w-0">
                <div className="font-medium truncate font-mono">{i.number}</div>
                <div className="text-xs text-muted-foreground truncate">{i.customer_name || "—"}</div>
              </div>
              <StatusBadge status={i.status} />
            </Link>
          )}
        />
      </div>

      {/* Recent activity */}
      <div className="border border-border bg-card mt-8">
        <div className="px-5 py-3 border-b border-border flex items-center justify-between">
          <div className="font-display font-medium flex items-center gap-2">
            <Activity className="h-4 w-4" strokeWidth={1.5} /> Recent activity
          </div>
        </div>
        <div className="divide-y divide-border">
          {(data.recent_activity || []).length === 0 ? (
            <div className="px-5 py-6 text-sm text-muted-foreground">No activity yet.</div>
          ) : (
            (data.recent_activity || []).map((a) => (
              <div key={a.id} className="px-5 py-3 flex items-center gap-4 hover-row">
                <div className="w-24 shrink-0 label-eyebrow">{a.module}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm truncate">
                    <span className="font-medium">{a.user_name || a.user_email}</span>{" "}
                    <span className="text-muted-foreground">{a.action}</span>{" "}
                    <span>{a.details}</span>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground shrink-0">{fmtRelative(a.timestamp)}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ExpiryPill({ days }) {
  if (days === null || days === undefined) return null;
  const tone =
    days <= 7 ? "bg-destructive/15 text-destructive border-destructive/30" :
    days <= 15 ? "bg-warning/15 text-[hsl(var(--warning))] border-warning/40" :
    "bg-primary/10 text-primary border-primary/30";
  return (
    <span className={`text-xs font-mono px-2 py-0.5 border rounded-sm shrink-0 ${tone}`}>
      {days}d
    </span>
  );
}

function ChartCard({ title, data, type, color }) {
  const rows = (data || []).map((d) => ({ month: d.month.slice(5), count: d.count }));
  return (
    <div className="border border-border bg-card">
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <div className="font-display font-medium">{title}</div>
        <TrendingUp className="h-4 w-4 text-muted-foreground" strokeWidth={1.5} />
      </div>
      <div className="p-3 h-60">
        <ResponsiveContainer width="100%" height="100%">
          {type === "bar" ? (
            <BarChart data={rows}>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={24} />
              <Tooltip
                cursor={{ fill: "hsl(var(--muted))" }}
                contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12, borderRadius: 4 }}
              />
              <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} />
            </BarChart>
          ) : (
            <LineChart data={rows}>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={24} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12, borderRadius: 4 }} />
              <Line type="monotone" dataKey="count" stroke={color} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
