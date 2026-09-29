import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";
import { AuthProvider, useAuth } from "./AuthContext.jsx";
import LoginPage from "./LoginPage.jsx";

function Root() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <LoginPage onSuccess={() => {}} />;
  }
  return <App />;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AuthProvider>
      <Root />
    </AuthProvider>
  </StrictMode>
);