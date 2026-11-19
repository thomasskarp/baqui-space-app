"use client";
// Los dos recuadros tipo buscador: [Gral. San Martín] → [¿Hacia dónde?]. En el celular, sin la flecha. En una sola fila, también en 375 px.
// El origen va siempre entero. En el celular el nombre del destino puede ir en 2 renglones (alto reservado, así
// el mapa no salta); en escritorio la barra mide 576 px y entra entero en uno, "Paraje Laguna El Lobo" incluido.
import { ArrowRight, Check, ChevronDown, MapPin } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { Destino } from "./datos";
import { T4 } from "./textos";
import s from "./demo.module.css";

export default function Buscador({
  destinos,
  elegido,
  onElegir,
}: {
  destinos: Destino[];
  elegido: Destino;
  onElegir: (id: string) => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const caja = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const lista = useRef<HTMLUListElement>(null);
  const idLista = useId();

  // Al abrir, el foco va a la opción elegida. Escape o tocar afuera cierra.
  useEffect(() => {
    if (!abierto) return;
    lista.current?.querySelector<HTMLButtonElement>("[aria-current='true']")?.focus({ preventScroll: true });
    const afuera = (e: PointerEvent) => {
      if (!caja.current?.contains(e.target as Node)) setAbierto(false);
    };
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Tab") setAbierto(false); // el foco se va de la lista: se cierra
      if (e.key === "Escape") {
        setAbierto(false);
        boton.current?.focus({ preventScroll: true });
      }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const items = Array.from(lista.current?.querySelectorAll<HTMLButtonElement>("button") ?? []);
        const i = items.indexOf(document.activeElement as HTMLButtonElement);
        const sig = e.key === "ArrowDown" ? (i + 1) % items.length : (i - 1 + items.length) % items.length;
        items[sig]?.focus({ preventScroll: true });
      }
    };
    document.addEventListener("pointerdown", afuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("pointerdown", afuera);
      document.removeEventListener("keydown", tecla);
    };
  }, [abierto]);

  const elegir = (id: string) => {
    onElegir(id);
    setAbierto(false);
    boton.current?.focus({ preventScroll: true });
  };

  return (
    <div
      ref={caja}
      role="group"
      aria-label={T4.buscador.etiqueta}
      className="glass relative z-30 grid grid-cols-2 items-stretch gap-1 rounded-2xl p-1.5 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] sm:gap-1"
    >
      {/* Desde: fijo. No se achica: "Gral. San Martín" siempre entero; el que se corta, si hace falta, es el destino. */}
      {/* Texto centrado en cada caja, igual que la respuesta (pedido de Facundo, 15/11). */}
      <div className="flex min-w-0 flex-col items-center justify-center rounded-xl px-2 py-2 text-center sm:px-3.5">
        <span className="text-xs text-ink-3">{T4.buscador.desde}</span>
        <span className="mt-0.5 flex items-center gap-1.5 whitespace-nowrap text-sm font-medium text-ink sm:gap-2 sm:text-[15px]">
          <span aria-hidden className="size-2 shrink-0 rounded-full bg-accent shadow-[0_0_0_3px_rgb(124_196_255/0.2)]" />
          <span>{T4.buscador.origen}</span>
        </span>
      </div>

      <span aria-hidden className="hidden items-center px-0.5 text-ink-3 sm:flex">
        <ArrowRight className="size-4" strokeWidth={2} />
      </span>

      {/* Hacia: se elige de la lista */}
      <div className="relative min-w-0">
        <button
          ref={boton}
          type="button"
          aria-expanded={abierto}
          aria-controls={idLista}
          aria-label={`${T4.buscador.placeholder} ${elegido.nombre}. ${T4.buscador.abrir}`}
          onClick={() => setAbierto((v) => !v)}
          className="flex min-h-11 size-full min-w-0 items-center gap-1 rounded-xl max-sm:min-h-[70px] bg-white/[0.07] px-2 py-2 text-center ring-1 ring-white/10 transition-[background-color,scale] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] hover:bg-white/[0.11] motion-safe:active:scale-[0.98] sm:gap-2 sm:px-3.5"
        >
          <span aria-hidden className="size-4 shrink-0" />
          <span className="flex min-w-0 flex-1 flex-col items-center">
            <span className="text-xs text-ink-3">{T4.buscador.placeholder}</span>
            <span className="mt-0.5 flex min-w-0 max-w-full items-center justify-center gap-1.5 text-sm font-semibold text-ink sm:text-[15px]">
              <MapPin aria-hidden className="size-3.5 shrink-0 text-ink-2 max-sm:hidden" strokeWidth={2.25} />
              <span className="truncate max-sm:line-clamp-2 max-sm:whitespace-normal max-sm:text-balance max-sm:leading-tight">
                {elegido.nombre}
              </span>
            </span>
          </span>
          <ChevronDown
            aria-hidden
            className={`size-4 shrink-0 text-ink-2 transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] ${abierto ? "rotate-180" : ""}`}
          />
        </button>

        {abierto && (
          <ul
            ref={lista}
            id={idLista}
            aria-label={T4.buscador.lista}
            className={`${s.pop} absolute right-0 top-[calc(100%+0.5rem)] z-30 w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-line bg-[#0b1220]/95 p-1.5 shadow-[0_24px_60px_-20px_rgb(0_0_0/0.9)] backdrop-blur-xl opaco:bg-[#0b1220]`}
          >
            {destinos.map((d) => {
              const actual = d.id === elegido.id;
              return (
                <li key={d.id}>
                  <button
                    type="button"
                    aria-current={actual ? "true" : undefined}
                    onClick={() => elegir(d.id)}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-[background-color,scale] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] hover:bg-white/[0.12] motion-safe:active:scale-[0.98] ${
                      actual ? "bg-white/[0.08]" : ""
                    }`}
                  >
                    <MapPin aria-hidden className="size-4 shrink-0 text-ink-3" strokeWidth={2} />
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-[15px] font-medium text-ink">{d.nombre}</span>
                      <span className="truncate text-xs text-ink-3">
                        {T4.buscador.opcionDetalle(T4.buscador.tipo(d.place_osm), d.caminos[0].km)}
                      </span>
                    </span>
                    {actual && <Check aria-hidden className="size-4 shrink-0 text-accent" strokeWidth={2.5} />}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
