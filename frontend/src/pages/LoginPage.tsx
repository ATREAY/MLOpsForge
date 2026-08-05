import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useLogin } from "@/api/auth";
import { Button, Card } from "@/components/ui";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();
  const navigate = useNavigate();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    login.mutate({ email, password }, { onSuccess: () => navigate("/") });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-bold text-slate-900">MLOpsForge</h1>
        <p className="mb-6 text-sm text-slate-500">Sign in to continue.</p>
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
            <label className="mb-1 block text-xs font-medium text-slate-600">Password</label>
            <input
              type="password"
              required
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {login.isError && <p className="text-sm text-red-600">Incorrect email or password.</p>}
          <Button type="submit" disabled={login.isPending}>
            {login.isPending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500">
          No account?{" "}
          <Link to="/register" className="font-medium text-slate-900 underline">
            Register
          </Link>
        </p>
      </Card>
    </div>
  );
}
