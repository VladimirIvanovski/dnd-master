import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { authApi } from "../api";
import { getToken } from "../api/client";

export function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (getToken()) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const resp =
        mode === "login"
          ? await authApi.login({ username, password })
          : await authApi.register({
              username,
              password,
              display_name: displayName || undefined,
            });
      authApi.applySession(resp);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col justify-center overflow-y-auto px-6 py-12">
      <p className="text-xs uppercase tracking-[0.35em] text-muted">Tabletop Reality Engine</p>
      <h1 className="display-text mt-3 text-4xl text-accent">
        {mode === "login" ? "Sign in" : "Create account"}
      </h1>
      <p className="mt-2 text-sm text-muted">
        Each account owns its own campaigns, characters, and memories.
      </p>

      <form onSubmit={(e) => void onSubmit(e)} className="panel mt-8 space-y-4 rounded-xl p-5">
        <label className="block text-sm">
          <span className="text-muted">Username</span>
          <input
            className="mt-1 w-full rounded border border-border bg-panel-2 px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            minLength={3}
          />
        </label>
        {mode === "register" ? (
          <label className="block text-sm">
            <span className="text-muted">Display name</span>
            <input
              className="mt-1 w-full rounded border border-border bg-panel-2 px-3 py-2"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </label>
        ) : null}
        <label className="block text-sm">
          <span className="text-muted">Password</span>
          <input
            type="password"
            className="mt-1 w-full rounded border border-border bg-panel-2 px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={8}
          />
        </label>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="display-text w-full rounded-lg border border-accent/50 bg-accent/20 px-5 py-2.5 text-accent hover:bg-accent/30 disabled:opacity-50"
        >
          {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Register"}
        </button>
      </form>

      <p className="mt-4 text-sm text-muted">
        {mode === "login" ? (
          <>
            No account?{" "}
            <button type="button" className="text-accent hover:underline" onClick={() => setMode("register")}>
              Register
            </button>
          </>
        ) : (
          <>
            Already registered?{" "}
            <button type="button" className="text-accent hover:underline" onClick={() => setMode("login")}>
              Sign in
            </button>
          </>
        )}
      </p>
      <p className="mt-6 text-xs text-muted">
        <Link to="/" className="hover:underline">
          Back
        </Link>
      </p>
    </div>
  );
}
