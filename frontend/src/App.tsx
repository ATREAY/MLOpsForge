import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { getToken } from "@/api/client";
import { Layout } from "@/components/Layout";
import DashboardPage from "@/pages/DashboardPage";
import DatasetsPage from "@/pages/DatasetsPage";
import ExperimentsPage from "@/pages/ExperimentsPage";
import LoginPage from "@/pages/LoginPage";
import ModelsPage from "@/pages/ModelsPage";
import RegisterPage from "@/pages/RegisterPage";
import TrainingPage from "@/pages/TrainingPage";

function RequireAuth({ children }: { children: ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route
        path="/datasets"
        element={
          <RequireAuth>
            <DatasetsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/experiments"
        element={
          <RequireAuth>
            <ExperimentsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/training"
        element={
          <RequireAuth>
            <TrainingPage />
          </RequireAuth>
        }
      />
      <Route
        path="/models"
        element={
          <RequireAuth>
            <ModelsPage />
          </RequireAuth>
        }
      />
    </Routes>
  );
}
