import { Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { AboutPage } from "./pages/AboutPage";
import { DiseaseDetailPage } from "./pages/DiseaseDetailPage";
import { DiseasesPage } from "./pages/DiseasesPage";
import { GenesPage } from "./pages/GenesPage";
import { GeneDetailPage } from "./pages/GeneDetailPage";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProteinsPage } from "./pages/ProteinsPage";
import { ProteinDetailPage } from "./pages/ProteinDetailPage";
import { SearchPage } from "./pages/SearchPage";
import { VariantDetailPage } from "./pages/VariantDetailPage";
import { VariantsPage } from "./pages/VariantsPage";
import { PublicationsPage } from "./pages/PublicationsPage";
import { PublicationDetailPage } from "./pages/PublicationDetailPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="genes" element={<GenesPage />} />
        <Route path="gene/:symbol" element={<GeneDetailPage />} />
        <Route path="proteins" element={<ProteinsPage />} />
        <Route path="protein/:accession" element={<ProteinDetailPage />} />
        <Route path="diseases" element={<DiseasesPage />} />
        <Route path="disease/:id" element={<DiseaseDetailPage />} />
        <Route path="variants" element={<VariantsPage />} />
        <Route path="publications" element={<PublicationsPage />} />
        <Route path="publication/:id" element={<PublicationDetailPage />} />
        <Route path="variant/:id" element={<VariantDetailPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
