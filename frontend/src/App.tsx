import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { getToken } from "./api/client";
import { CreateCampaignPage } from "./pages/CreateCampaignPage";
import { CreateCharacterPage } from "./pages/CreateCharacterPage";
import { GamePage } from "./pages/GamePage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";

function RequireAuth() {
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/campaigns/new" element={<CreateCampaignPage />} />
        <Route path="/characters/new" element={<CreateCharacterPage />} />
        <Route path="/game/:campaignId/:characterId" element={<GamePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
