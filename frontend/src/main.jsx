import React from "react";
import ReactDOM from "react-dom/client";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import App from "./App";
import ShowcasePage from "./ShowcasePage.jsx";
import "./styles.css";
import "./showcase.css";

const isShowcase = /\/showcase\/?$/.test(window.location.pathname);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <FluentProvider theme={webLightTheme}>
      {isShowcase ? <ShowcasePage /> : <App />}
    </FluentProvider>
  </React.StrictMode>,
);
