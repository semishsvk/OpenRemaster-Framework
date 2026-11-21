import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

// Both signals are published together. Some WebView2 accessibility providers
// expose the document name without exposing the landmark's AutomationId.
function Studio() {
  React.useEffect(() => {
    const main = document.querySelector("main");
    if (!main) return;
    const loadingTitle = document.title;
    let frame = requestAnimationFrame(() => {
      frame = requestAnimationFrame(() => {
        main.id = "openremaster-studio-ready-v1";
        document.title = "OpenRemaster Studio workspace";
      });
    });
    return () => {
      cancelAnimationFrame(frame);
      if (main.id === "openremaster-studio-ready-v1") main.removeAttribute("id");
      document.title = loadingTitle;
    };
  }, []);
  return <App />;
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><Studio /></React.StrictMode>);
