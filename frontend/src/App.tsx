import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import CatalogPage from "./pages/CatalogPage";
import DashboardPage from "./pages/DashboardPage";
import MapPage from "./pages/MapPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<MapPage />} />
        <Route path="structures/:id" element={<MapPage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
