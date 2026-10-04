import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout, Notice } from "./components/Layout";
import { DesignerPage } from "./pages/DesignerPage";
import { StoryPage } from "./pages/StoryPage";
import { BenchmarkPage, MaterialsPage, MethodsPage, OptimizerPage, OverviewPage, RunPage, RunsPage } from "./pages/OtherPages";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<StoryPage />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/design" element={<DesignerPage />} />
          <Route path="/optimize" element={<OptimizerPage />} />
          <Route path="/materials" element={<MaterialsPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/runs/:id" element={<RunPage />} />
          <Route path="/benchmark" element={<BenchmarkPage />} />
          <Route path="/methods" element={<MethodsPage />} />
          <Route path="*" element={<Notice>Page not found.</Notice>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
