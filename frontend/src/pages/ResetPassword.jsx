import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { KeyRound, Mail, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const requestReset = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      setSent(true);
      toast.success("If the email is registered, a reset link will be sent shortly.");
      return data;
    } catch (err) {
      toast.error(formatApiError(err));
    } finally { setBusy(false); }
  };

  const completeReset = async (e) => {
    e.preventDefault();
    if (password.length < 12) return toast.error("Password must be at least 12 characters.");
    if (password !== confirmPassword) return toast.error("Password confirmation does not match.");
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      toast.success("Password updated. Please sign in with your new password.");
      navigate("/login", { replace: true });
    } catch (err) {
      toast.error(formatApiError(err));
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-background p-6">
      <div className="w-full max-w-md border border-border bg-card p-7 sm:p-9">
        <div className="mb-8">
          <img src="/logisource-logo-light.png" alt="LogiSource Digital" className="h-12 w-auto object-contain" />
          <div className="label-eyebrow mt-6">LogiSource Digital · Integrated System</div>
        </div>
        {token ? (
          <>
            <div className="flex h-11 w-11 items-center justify-center border border-border bg-muted/40 mb-4"><KeyRound className="h-5 w-5" /></div>
            <h1 className="text-2xl font-display font-semibold tracking-tight">Create a new password</h1>
            <p className="text-sm text-muted-foreground mt-2">Use at least 12 characters. This link can only be used once.</p>
            <form onSubmit={completeReset} className="mt-7 space-y-4">
              <div className="space-y-1.5"><Label htmlFor="new-password">New password</Label><Input id="new-password" type="password" minLength={12} maxLength={128} required autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
              <div className="space-y-1.5"><Label htmlFor="confirm-password">Confirm new password</Label><Input id="confirm-password" type="password" minLength={12} maxLength={128} required autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} /></div>
              <Button type="submit" className="w-full" size="lg" disabled={busy}>{busy ? "Updating password…" : "Update password"}</Button>
            </form>
            <Link to="/reset-password" className="mt-4 inline-block text-sm text-primary hover:underline">Request a new reset link</Link>
          </>
        ) : (
          <>
            <div className="flex h-11 w-11 items-center justify-center border border-border bg-muted/40 mb-4"><Mail className="h-5 w-5" /></div>
            <h1 className="text-2xl font-display font-semibold tracking-tight">Forgot your password?</h1>
            <p className="text-sm text-muted-foreground mt-2">Enter the email address associated with your LogiSource CRM account. If it is registered, we will send a reset link.</p>
            {sent ? (
              <div className="mt-6 border border-border bg-muted/30 p-4 text-sm leading-relaxed">Request received. Please check your inbox and spam folder. If the email is registered, a reset link will arrive shortly.</div>
            ) : (
              <form onSubmit={requestReset} className="mt-7 space-y-4">
                <div className="space-y-1.5"><Label htmlFor="reset-email">Email</Label><Input id="reset-email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" /></div>
                <Button type="submit" className="w-full" size="lg" disabled={busy}>{busy ? "Sending request…" : "Send reset link"}</Button>
              </form>
            )}
          </>
        )}
        <Link to="/login" className="mt-6 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Back to sign in</Link>
      </div>
    </div>
  );
}
