import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";
import { AuthProvider, useAuth } from "./AuthContext.jsx";
import LoginPage from "./LoginPage.jsx";
import CambioObligatorio from "./CambioObligatorio.jsx";

function Root() {
  const { isAuthenticated, listo, user } = useAuth();
  if (!listo) return <div className="loading-wrap"><div className="spinner"/><span className="loading-text">Cargando...</span></div>;
  if (!isAuthenticated) return <LoginPage onSuccess={() => {}} />;
  if (user?.debe_cambiar_password) return <CambioObligatorio />;
  return <App />;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AuthProvider>
      <Root />
    </AuthProvider>
  </StrictMode>
);
