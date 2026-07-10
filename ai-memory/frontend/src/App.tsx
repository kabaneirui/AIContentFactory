import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DecisionPage } from "./pages/DecisionPage";
import { HomePage } from "./pages/HomePage";
import { ImportPage } from "./pages/ImportPage";
import { LearningPage } from "./pages/LearningPage";
import { PredictPage } from "./pages/PredictPage";
import { PromptsPage } from "./pages/PromptsPage";
import { VideoDetailPage } from "./pages/VideoDetailPage";
import { VideosPage } from "./pages/VideosPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="decision" element={<DecisionPage />} />
        <Route path="videos" element={<VideosPage />} />
        <Route path="videos/:videoId" element={<VideoDetailPage />} />
        <Route path="learning" element={<LearningPage />} />
        <Route path="predict" element={<PredictPage />} />
        <Route path="prompts" element={<PromptsPage />} />
        <Route path="import" element={<ImportPage />} />
      </Route>
    </Routes>
  );
}
