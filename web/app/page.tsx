"use client";

import { Activity, CircleHelp, Database, FileSearch, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import Batch from "./batch";
import CardPage, { useCard } from "./card";
import Live from "./live";
import { startTour, TOUR_KEY } from "./tour";

export default function Page() {
  const [tab, setTab] = useState<"live" | "batch" | "card">("live");
  const { card, error } = useCard();

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
          <button aria-current={tab === "card" ? "page" : undefined} onClick={() => setTab("card")}>
            <Database size={15} aria-hidden="true" />Dữ liệu và mô hình
          </button>
        </nav>
        <button className="ghost" data-tour="help" onClick={() => startTour(setTab)}>
          <CircleHelp size={15} aria-hidden="true" />Hướng dẫn
        </button>
      </header>
      <div hidden={tab !== "live"}><Live devices={card?.devices ?? []} thr={card?.model?.threshold.value} /></div>
      <div hidden={tab !== "batch"}><Batch /></div>
      <div hidden={tab !== "card"}><CardPage card={card} error={error} /></div>
    </>
  );
}
