"use client";

import { Activity, CircleHelp, FileSearch, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import Batch from "./batch";
import Live from "./live";
import { startTour, TOUR_KEY } from "./tour";

export default function Page() {
  const [tab, setTab] = useState<"live" | "batch">("live");

  useEffect(() => {        // tự mở hướng dẫn một lần cho người mới, chờ dữ liệu đầu tiên về
    if (localStorage.getItem(TOUR_KEY)) return;
    const begun = Date.now();
    const id = setInterval(() => {
      const ready = document.querySelector('[data-tour="incidents"] tbody tr, [data-tour="stats"] strong');
      if (ready || Date.now() - begun > 8000) { clearInterval(id); startTour(setTab); }
    }, 300);
    return () => clearInterval(id);
  }, []);

  return (
    <>
      <header className="appbar">
        <div className="brand">
          <span className="mark"><ShieldCheck size={18} aria-hidden="true" /></span>
          <strong>Giám sát xâm nhập mạng</strong>
        </div>
        <nav aria-label="Chức năng">
          <button aria-current={tab === "live" ? "page" : undefined} onClick={() => setTab("live")}>
            <Activity size={15} aria-hidden="true" />Giám sát trực tiếp
          </button>
          <button aria-current={tab === "batch" ? "page" : undefined} onClick={() => setTab("batch")}>
            <FileSearch size={15} aria-hidden="true" />Phân tích file
          </button>
        </nav>
        <button className="ghost" data-tour="help" onClick={() => startTour(setTab)}>
          <CircleHelp size={15} aria-hidden="true" />Hướng dẫn
        </button>
      </header>
      <div hidden={tab !== "live"}><Live /></div>
      <div hidden={tab !== "batch"}><Batch /></div>
    </>
  );
}
