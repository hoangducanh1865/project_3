"use client";

import { useState } from "react";
import Batch from "./batch";
import Live from "./live";

export default function Page() {
  const [tab, setTab] = useState<"live" | "batch">("live");
  return (
    <>
      <header className="top">
        <h1>Giám sát xâm nhập mạng</h1>
        <p>Phát hiện tấn công Out-of-Domain (OOD) và đề xuất biện pháp ứng phó</p>
        <nav>
          <button aria-pressed={tab === "live"} onClick={() => setTab("live")}>Giám sát trực tiếp</button>
          <button aria-pressed={tab === "batch"} onClick={() => setTab("batch")}>Phân tích file</button>
        </nav>
      </header>
      <div hidden={tab !== "live"}><Live /></div>
      <div hidden={tab !== "batch"}><Batch /></div>
    </>
  );
}
