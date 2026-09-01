import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Package,
  FileText,
  Receipt,
  FolderKanban,
  KeyRound,
  BadgeCheck,
  Zap,
  History,
  UserCog,
  Settings,
  Sun,
  Moon,
  LogOut,
  Menu,
  X,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import api, { formatApiError } from "@/lib/api";
import { LAYOUT, AUTH } from "@/constants/testIds";

const NAV_SECTIONS = [
  {
    label: "Overview",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Dashboard", exact: true },
    ],
  },
  {
    label: "Sales",
    items: [
      { to: "/customers", icon: Users, label: "Customers" },
      { to: "/products", icon: Package, label: "Products" },
      { to: "/quotations", icon: FileText, label: "Quotations" },
      { to: "/invoices", icon: Receipt, label: "Invoices" },
    ],
  },
  {
    label: "Operations",
    items: [
      { to: "/projects", icon: FolderKanban, label: "Projects" },
      { to: "/accounts", icon: KeyRound, label: "Credential Vault" },
      { to: "/licenses", icon: BadgeCheck, label: "Licenses" },
      { to: "/logi-license", icon: Zap, label: "LogiLicense" },
    ],
  },
  {
    label: "Admin",
    items: [
      { to: "/activity-logs", icon: History, label: "Activity Logs" },
      { to: "/users", icon: UserCog, label: "User Management", adminOnly: true },
      { to: "/settings", icon: Settings, label: "Website Settings", adminOnly: true },
    ],
  },
];

function SidebarNav({ user, onNavigate }) {
  return (
    <nav className="flex flex-col gap-6 px-3 pb-6" data-testid={LAYOUT.sidebar}>
      {NAV_SECTIONS.map((section) => {
        const items = section.items.filter((i) => !i.adminOnly || user?.role === "admin");
        if (items.length === 0) return null;
        return (
          <div key={section.label}>
            <div className="label-eyebrow px-3 mb-2">{section.label}</div>
            <div className="flex flex-col">
              {items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.exact}
                  onClick={onNavigate}
                  data-testid={`sidebar-link-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
                  className={({ isActive }) =>
                    [
                      "group flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-sm border border-transparent",
                      "transition-colors",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-foreground hover:bg-muted",
                    ].join(" ")
                  }
                >
                  <item.icon className="h-4 w-4" strokeWidth={1.5} />
                  <span className="flex-1">{item.label}</span>
                  <ChevronRight className="h-3.5 w-3.5 opacity-40 group-hover:opacity-100" />
                </NavLink>
              ))}
            </div>
          </div>
        );
      })}
    </nav>
  );
}

function ChangePasswordDialog({ open, onOpenChange }) {
  const [oldp, setOldp] = useState("");
  const [newp, setNewp] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/auth/change-password", { old_password: oldp, new_password: newp });
      toast.success("Password updated");
      setOldp("");
      setNewp("");
      onOpenChange(false);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle className="font-display">Change Password</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Current Password</Label>
            <Input
              type="password"
              value={oldp}
              onChange={(e) => setOldp(e.target.value)}
              required
              data-testid="change-password-old-input"
            />
          </div>
          <div className="space-y-1.5">
            <Label>New Password</Label>
            <Input
              type="password"
              value={newp}
              onChange={(e) => setNewp(e.target.value)}
              required
              minLength={6}
              data-testid="change-password-new-input"
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={busy} data-testid="change-password-submit">
              {busy ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pwdOpen, setPwdOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    document.title = "LogiSource Integrated System";
  }, []);

  const initials =
    (user?.name || user?.email || "??")
      .split(" ")
      .map((s) => s[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Sidebar - desktop */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 w-64 border-r border-border bg-card flex-col">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-border">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="h-8 w-8 bg-primary text-primary-foreground grid place-items-center font-display font-semibold text-sm rounded-sm">
              LS
            </div>
            <div className="leading-tight">
              <div className="font-display font-semibold text-sm">LogiSource</div>
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Integrated System</div>
            </div>
          </Link>
        </div>
        <div className="flex-1 overflow-y-auto pt-4">
          <SidebarNav user={user} />
        </div>
        <div className="border-t border-border px-4 py-3">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Signed in as</div>
          <div className="text-sm font-medium truncate">{user?.name || user?.email}</div>
          <div className="text-xs text-muted-foreground capitalize">{user?.role}</div>
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40" onClick={() => setMobileOpen(false)}>
          <div className="absolute inset-0 bg-black/50" />
          <aside className="absolute inset-y-0 left-0 w-72 bg-card border-r border-border flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="h-16 flex items-center justify-between px-5 border-b border-border">
              <span className="font-display font-semibold">LogiSource</span>
              <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto pt-4">
              <SidebarNav user={user} onNavigate={() => setMobileOpen(false)} />
            </div>
          </aside>
        </div>
      )}

      {/* Main column */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* Topbar */}
        <header
          className="sticky top-0 z-30 h-16 border-b border-border bg-background/80 backdrop-blur-xl flex items-center px-4 lg:px-8 gap-3"
          data-testid={LAYOUT.topbar}
        >
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setMobileOpen(true)}
            data-testid="topbar-mobile-menu-button"
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="flex-1" />

          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            data-testid={LAYOUT.themeToggle}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" strokeWidth={1.5} /> : <Moon className="h-4 w-4" strokeWidth={1.5} />}
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                data-testid={LAYOUT.userMenu}
                className="flex items-center gap-2 border border-border rounded-sm px-2 py-1.5 hover:bg-muted transition-colors"
              >
                <div className="h-7 w-7 bg-primary text-primary-foreground grid place-items-center text-xs font-semibold rounded-sm">
                  {initials}
                </div>
                <div className="hidden sm:block text-left leading-tight">
                  <div className="text-xs font-medium">{user?.name}</div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{user?.role}</div>
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>{user?.email}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => setPwdOpen(true)}
                data-testid={AUTH.changePasswordButton}
              >
                <KeyRound className="h-4 w-4 mr-2" strokeWidth={1.5} /> Change Password
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={async () => {
                  await logout();
                  navigate("/login");
                }}
                data-testid={AUTH.logoutButton}
                className="text-destructive focus:text-destructive"
              >
                <LogOut className="h-4 w-4 mr-2" strokeWidth={1.5} /> Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <main className="flex-1 px-4 lg:px-8 py-6 lg:py-8">
          <Outlet />
        </main>

        <footer className="border-t border-border px-4 lg:px-8 py-4 text-xs text-muted-foreground flex flex-wrap gap-2 items-center justify-between">
          <div>© {new Date().getFullYear()} LogiSource Digital. All rights reserved.</div>
          <div className="font-mono">Digital. Reliable. Connected.</div>
        </footer>
      </div>

      <ChangePasswordDialog open={pwdOpen} onOpenChange={setPwdOpen} />
    </div>
  );
}
