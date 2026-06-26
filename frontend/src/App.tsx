import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import ApplicationsPage from "./pages/ApplicationsPage";
import CatalogPage from "./pages/CatalogPage";
import DashboardPage from "./pages/DashboardPage";
import MapPage from "./pages/MapPage";
import ParseReviewPage from "./pages/ParseReviewPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<MapPage />} />
        <Route path="structures/:id" element={<MapPage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="parse" element={<ParseReviewPage />} />
        <Route path="applications" element={<ApplicationsPage />} />
      </Route>
    </Routes>
  );
}
