import "./theme.css";

import { createRoot } from "react-dom/client";

import { App } from "./app.tsx";
import { connect } from "./bridge.ts";

connect().then((bridge) => createRoot(document.getElementById("root")!).render(<App bridge={bridge} />));
