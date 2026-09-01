import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Eye, EyeOff, LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { formatApiError } from "@/lib/api";
import { AUTH } from "@/constants/testIds";

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  if (loading) {
    return <div className="min-h-screen grid place-items-center text-sm text-muted-foreground">Loading…</div>;
  }
  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password, remember);
      toast.success("Welcome back");
      navigate("/", { replace: true });
    } catch (err) {
      const msg = formatApiError(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* Left brand panel */}
      <div className="hidden lg:flex flex-col justify-between border-r border-border p-12 bg-card">
        <div>
          <img
            src="/logisource-logo-light.png"
            alt="LogiSource Digital"
            className="h-16 w-auto object-contain"
          />
        </div>

        <div className="max-w-md">
          <div className="label-eyebrow mb-4">Internal Business OS</div>
          <h1 className="text-4xl font-display font-semibold leading-tight tracking-tight">
            The single source of truth for customers, deals, and credentials.
          </h1>
          <p className="mt-5 text-muted-foreground leading-relaxed">
            One command center for quotations, invoices, projects and every account credential
            your team relies on — securely encrypted, precisely tracked.
          </p>

          <div className="mt-10 grid grid-cols-2 gap-4">
            {[
              { k: "Modules", v: "11" },
              { k: "Roles", v: "2" },
              { k: "Encryption", v: "AES-256" },
              { k: "Format", v: "PDF · XLSX" },
            ].map((f) => (
              <div key={f.k} className="border border-border p-4">
                <div className="label-eyebrow">{f.k}</div>
                <div className="font-display text-2xl font-semibold mt-1">{f.v}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="text-xs text-muted-foreground font-mono">
          Digital. Reliable. Connected.
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex items-center justify-center p-6 lg:p-12">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8">
            <img
              src="/logisource-logo-light.png"
              alt="LogiSource Digital"
              className="h-14 w-auto object-contain"
            />
          </div>

          <div className="label-eyebrow mb-2">Sign in</div>
          <h2 className="text-3xl font-display font-semibold tracking-tight">Welcome back</h2>
          <p className="text-sm text-muted-foreground mt-2">
            Enter your credentials to access the LogiSource internal system.
          </p>

          <form onSubmit={submit} className="mt-8 space-y-5">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@logisource.com"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid={AUTH.emailInput}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={show ? "text" : "password"}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  data-testid={AUTH.passwordInput}
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                  aria-label={show ? "Hide password" : "Show password"}
                  data-testid="login-password-toggle"
                >
                  {show ? <EyeOff className="h-4 w-4" strokeWidth={1.5} /> : <Eye className="h-4 w-4" strokeWidth={1.5} />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <Checkbox
                  checked={remember}
                  onCheckedChange={(v) => setRemember(!!v)}
                  data-testid={AUTH.rememberCheckbox}
                />
                <span>Remember me</span>
              </label>
              <span className="text-xs text-muted-foreground">Session times out automatically</span>
            </div>

            {error && (
              <div className="border border-destructive/40 bg-destructive/10 text-destructive text-sm px-3 py-2 rounded-sm">
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              size="lg"
              disabled={busy}
              data-testid={AUTH.submitButton}
            >
              <LogIn className="h-4 w-4 mr-2" strokeWidth={1.5} />
              {busy ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
