import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

export default function BelowSelect({ value, options, onChange, disabled = false, placeholder = "请选择" }) {
  const [open, setOpen] = useState(false);
  const [rect, setRect] = useState(null);
  const trigger = useRef(null);
  const menu = useRef(null);
  const listId = useId();
  const selected = options.find((option) => option.value === value);
  useEffect(() => {
    if (!open) return undefined;
    const close = (event) => {
      if (!trigger.current?.contains(event.target) && !menu.current?.contains(event.target)) setOpen(false);
    };
    const reposition = () => setRect(trigger.current?.getBoundingClientRect() || null);
    document.addEventListener("pointerdown", close);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    return () => {
      document.removeEventListener("pointerdown", close);
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
    };
  }, [open]);
  const toggle = () => {
    if (disabled) return;
    setRect(trigger.current?.getBoundingClientRect() || null);
    setOpen((current) => !current);
  };
  return <>
    <button ref={trigger} type="button" className="below-select-trigger" disabled={disabled} aria-haspopup="listbox" aria-expanded={open} aria-controls={open ? listId : undefined} onClick={toggle} onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}>
      <span>{selected?.label || placeholder}</span><span aria-hidden="true">⌄</span>
    </button>
    {open && rect && createPortal(<div ref={menu} id={listId} role="listbox" className="below-select-menu" style={{ left: rect.left, top: rect.bottom + 4, width: rect.width, maxHeight: Math.max(80, window.innerHeight - rect.bottom - 12) }}>
      {options.map((option) => <button key={option.value} type="button" role="option" aria-selected={option.value === value} onClick={() => { onChange(option.value); setOpen(false); trigger.current?.focus(); }}>{option.label}</button>)}
    </div>, document.body)}
  </>;
}
