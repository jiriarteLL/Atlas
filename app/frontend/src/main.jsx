import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./fuentes.css";
import "./styles.css";
import "./diseno/diseno.css";
import App from "./App.jsx";
import { AuthProvider, useAuth } from "./AuthContext.jsx";
import LoginPage from "./LoginPage.jsx";
import CambioObligatorio from "./CambioObligatorio.jsx";
import { AmbienteProvider, useAmbiente } from "./diseno/ambiente.jsx";
import Escenario from "./diseno/Escenario.jsx";
import Intro from "./diseno/Intro.jsx";

// La intro se muestra una vez por pestaña (no en cada recarga).
function introVista() { try { return sessionStorage.getItem("inventario_intro") === "1"; } catch { return false; } }
function marcarIntro() { try { sessionStorage.setItem("inventario_intro", "1"); } catch { /* sin storage */ } }

function Root() {
  const { isAuthenticated, listo, user } = useAuth();
  const { setEntrado } = useAmbiente();
  const [intro, setIntro] = useState(() => !introVista());

  let contenido;
  if (!listo) contenido = <div className="ll-login-velo"><div className="spinner" /></div>;
  else if (isAuthenticated && user?.debe_cambiar_password) contenido = <CambioObligatorio />;
  else if (isAuthenticated) contenido = <App />;
  else if (intro) contenido = <Intro alEntrar={() => { marcarIntro(); setIntro(false); }} />;
  else contenido = <LoginPage />;

  // Con la sesion recuperada (o la intro ya vista) la esfera arranca en su posicion de fondo.
  const enFondo = listo && (isAuthenticated || !intro);
  useEffect(() => { if (enFondo) setEntrado(true); }, [enFondo, setEntrado]);
  return <Escenario>{contenido}</Escenario>;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AmbienteProvider>
      <AuthProvider>
        <Root />
      </AuthProvider>
    </AmbienteProvider>
  </StrictMode>
);
