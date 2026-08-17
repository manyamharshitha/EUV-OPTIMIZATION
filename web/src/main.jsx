import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";
// Loaded last: the professional pass overrides the earlier visual layers.
import "./professional.css";
// Type scale, filled buttons, dark mark, light plasma panel.
import "./refine.css";
// Loaded last: redefines the tokens the layers above read from, so removing
// this one line returns the app to the previous theme intact.
import "./enterprise.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
