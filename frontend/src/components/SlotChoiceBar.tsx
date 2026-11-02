// 槽位追问：ABCD 选项；D=其他情况时展开自由输入

import { useEffect, useRef, useState } from "react";
import type { SlotOption } from "../api/types";

interface Props {
  busy: boolean;
  prompt: string;
  options: SlotOption[];
  onChoose: (text: string) => void;
  onCancel?: () => void;
}

export default function SlotChoiceBar({ busy, prompt, options, onChoose, onCancel }: Props) {
  const [otherMode, setOtherMode] = useState(false);
  const [otherText, setOtherText] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setOtherMode(false);
    setOtherText("");
  }, [prompt]);

  useEffect(() => {
    if (otherMode) taRef.current?.focus();
  }, [otherMode]);

  const pick = (opt: SlotOption) => {
    if (busy) return;
    if (opt.key === "D") {
      setOtherMode(true);
      return;
    }
    onChoose(`${opt.key}. ${opt.label}`);
  };

  const submitOther = () => {
    const t = otherText.trim();
    if (!t || busy) return;
    onChoose(t);
    setOtherText("");
    setOtherMode(false);
  };

  return (
    <div className="input-area slot-choice-area">
      <p className="slot-prompt">{prompt}</p>
      {!otherMode ? (
        <div className="slot-options">
          {options.map((opt) => (
            <button
              key={opt.key}
              type="button"
              className={`slot-opt ${opt.key === "D" ? "slot-opt-other" : ""}`}
              disabled={busy}
              onClick={() => pick(opt)}
            >
              <span className="slot-key">{opt.key}</span>
              <span className="slot-label">{opt.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <div className="input-row">
          <textarea
            ref={taRef}
            rows={2}
            value={otherText}
            onChange={(e) => setOtherText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submitOther();
              }
            }}
            placeholder="请简要描述其他情况…"
            disabled={busy}
          />
          <button
            className="btn-primary"
            type="button"
            disabled={busy || !otherText.trim()}
            onClick={submitOther}
          >
            {busy ? "处理中…" : "发送"}
          </button>
          <button
            className="btn-ghost"
            type="button"
            disabled={busy}
            onClick={() => {
              setOtherMode(false);
              setOtherText("");
            }}
          >
            返回选项
          </button>
        </div>
      )}
      {onCancel && (
        <p className="input-hint">
          <button type="button" className="linkish" disabled={busy} onClick={onCancel}>
            跳过引导，直接自由提问
          </button>
        </p>
      )}
    </div>
  );
}
