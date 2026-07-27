import { Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import DashboardPage from "@/pages/DashboardPage";
import DatasetsPage from "@/pages/DatasetsPage";
import ExperimentsPage from "@/pages/ExperimentsPage";
import ModelsPage from "@/pages/ModelsPage";
import TrainingPage from "@/pages/TrainingPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/datasets" element={<DatasetsPage />} />
        <Route path="/experiments" element={<ExperimentsPage />} />
        <Route path="/training" element={<TrainingPage />} />
        <Route path="/models" element={<ModelsPage />} />
      </Routes>
    </Layout>
  );
}
