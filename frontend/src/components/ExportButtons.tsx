import { useState } from "react";
import { api } from "../api/client";

interface Props {
  title: string;
  markdown: string;
}

export default function ExportButtons({ title, markdown }: Props) {
  const [busy, setBusy] = useState("");

  const run = async (format: "docx" | "pdf") => {
    setBusy(format);
    try {
      await api.downloadExport(title, markdown, format);
    } catch (e) {
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: e instanceof Error ? e.message : "导出失败", type: "error" },
        }),
      );
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="btn-row">
      <button type="button" className="btn-gold" disabled={!!busy || !markdown.trim()} onClick={() => void run("docx")}>
        {busy === "docx" ? "导出中…" : "导出 Word"}
      </button>
      <button type="button" className="btn-ghost" disabled={!!busy || !markdown.trim()} onClick={() => void run("pdf")}>
        {busy === "pdf" ? "导出中…" : "导出 PDF"}
      </button>
    </div>
  );
}
