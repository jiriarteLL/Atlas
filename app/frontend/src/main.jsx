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

// Secuencia de entrada (como el prototipo): en el login el globo se ve entero; al ingresar, la tarjeta
// se desvanece, la camara se sumerge en el globo y la app aparece con un fundido.
const SALIDA_MS = 650;

function Root() {
  const { isAuthenticated, listo, user } = useAuth();
  const { setEntrado } = useAmbiente();
  const [intro, setIntro] = useState(() => !introVista());
  const [vista, setVista] = useState("inicio");   // inicio | login | cambio | saliendo | app

  const destino = !listo ? "inicio" : !isAuthenticated ? "login" : user?.debe_cambiar_password ? "cambio" : "app";
  useEffect(() => {
    // Solo se anima la entrada cuando se viene del login; con la sesion recuperada se entra directo.
    const t = setTimeout(() => setVista((v) => (destino === "app" && (v === "login" || v === "cambio") ? "saliendo" : destino)), 0);
    return () => clearTimeout(t);
  }, [destino]);
  useEffect(() => {
    if (vista !== "saliendo") return undefined;
    const t = setTimeout(() => setVista("app"), SALIDA_MS);
    return () => clearTimeout(t);
  }, [vista]);

  const enFondo = vista === "saliendo" || vista === "app";
  useEffect(() => { setEntrado(enFondo); }, [enFondo, setEntrado]);

  let contenido;
  if (vista === "inicio") contenido = <div className="ll-login-velo"><div className="spinner" /></div>;
  else if (vista === "cambio") contenido = <CambioObligatorio />;
  else if (vista === "app") contenido = <App />;
  else if (vista === "login" && intro) contenido = <Intro alEntrar={() => { marcarIntro(); setIntro(false); }} />;
  else contenido = <LoginPage saliendo={vista === "saliendo"} />;
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
