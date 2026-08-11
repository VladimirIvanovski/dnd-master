import { Navigate, Route, Routes } from "react-router-dom";
import { CreateCampaignPage } from "./pages/CreateCampaignPage";
import { CreateCharacterPage } from "./pages/CreateCharacterPage";
import { GamePage } from "./pages/GamePage";
import { HomePage } from "./pages/HomePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/campaigns/new" element={<CreateCampaignPage />} />
      <Route path="/characters/new" element={<CreateCharacterPage />} />
      <Route path="/game/:campaignId/:characterId" element={<GamePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
