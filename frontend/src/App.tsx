import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { OverviewPage } from "./pages/OverviewPage";
import { CaseExplorerPage } from "./pages/CaseExplorerPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { InvestigationsPage } from "./pages/InvestigationsPage";
import { InvestigationDetailPage } from "./pages/InvestigationDetailPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="dashboard" element={<Navigate to="/" replace />} />
          <Route path="cases" element={<CaseExplorerPage />} />
          <Route path="cases/:caseId" element={<CaseDetailPage />} />
          <Route path="investigations" element={<InvestigationsPage />} />
          <Route path="investigations/:caseId" element={<InvestigationDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
