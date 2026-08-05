import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useLogin, useRegister } from "@/api/auth";
import { Button, Card } from "@/components/ui";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const register = useRegister();
  const login = useLogin();
  const navigate = useNavigate();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    register.mutate(
      { email, password, full_name: fullName || undefined },
      { onSuccess: () => login.mutate({ email, password }, { onSuccess: () => navigate("/") }) },
    );
  }

  const error = register.isError
    ? "Could not create that account (email may already be registered)."
    : login.isError
      ? "Account created, but sign-in failed — try logging in manually."
      : null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-bold text-slate-900">MLOpsForge</h1>
        <p className="mb-6 text-sm text-slate-500">Create an account.</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Email</label>
            <input
              type="email"
              required
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Full name (optional)</label>
            <input
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Password</label>
            <input
              type="password"
              required
              minLength={8}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={register.isPending || login.isPending}>
            {register.isPending || login.isPending ? "Creating account…" : "Create account"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-slate-900 underline">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
