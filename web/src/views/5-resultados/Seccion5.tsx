"use client";
import { useEffect, useRef, useState, type RefObject } from "react";
import { ArrowDown, ArrowUp, Check, Copy, Droplets, FlaskConical, Minus, Satellite, Sun, TrendingUp, Waves } from "lucide-react";
import Seccion from "@/components/Seccion";
import Estado from "@/components/Estado";
import Fuente from "@/components/Fuente";
import Reveal from "@/components/Reveal";
import Encabezado from "@/components/Encabezado";
import Final from "@/components/Final";
import { useMenosMovimiento } from "@/components/hooks";
import datos from "@/data/resultados.json";
import { textos as t } from "./textos";

/* ---------- Formato (coma decimal, punto de miles; igual en servidor y navegador) ---------- */

function fmt(n: number, decimales = 1): string {
  const [entero, dec] = Math.abs(n).toFixed(decimales).split(".");
  const miles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${n < 0 ? "-" : ""}${miles}${dec ? `,${dec}` : ""}`;
}

/* ---------- Datos medidos (todo sale del JSON; ver sus "_fuente") ---------- */

// El secado (media vida) no se muestra: es una serie de pasadas y BAQUI es una consulta de hoy.
const { radar, medicion, eco, suben, agua, zona_abierta: abierta } = datos;
const subidaDb = eco.subida_db;
const DECIMALES_DB = 2;
/** Puntos del eje que subieron más de 1 dB, de cada 10 (de 1 a 3 dB más los de más de 3 dB). */
const subenDeCada10 = Math.round((suben.pct_1_a_3_db + suben.pct_mas_de_3_db) / 10);
/**
 * Decimales justos para que el porcentaje de agua no se lea como cero (0,006 → 3), con tope de 6.
 * Si el dato es 0 o no es un número válido, 1 decimal (log10 daría infinito y toFixed tiraría error).
 */
const decimalesAgua =
  Number.isFinite(agua.pct_con_agua) && agua.pct_con_agua > 0
    ? Math.min(6, Math.max(1, -Math.floor(Math.log10(agua.pct_con_agua))))
    : 1;

/* ---------- Hooks locales ---------- */

/** true una sola vez, cuando el elemento (chico) entra bien en pantalla. */
function useAlEntrar(ref: RefObject<Element | null>, umbral = 0.3): boolean {
  const [entro, setEntro] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setEntro(true);
          io.disconnect();
        }
      },
      { threshold: umbral },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref, umbral]);
  return entro;
}

/**
 * Cuenta de 0 al valor final al entrar en pantalla.
 * En el servidor y sin JS muestra el valor final; con menos movimiento no anima.
 */
function useContador(fin: number, activo: boolean, menos: boolean, duracion = 1600): number {
  const [valor, setValor] = useState(fin);
  const arranco = useRef(false);

  // Al montar: si la persona acepta movimiento y todavía no se vio, arranca en 0.
  useEffect(() => {
    const quieto = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!quieto && !arranco.current) setValor(0);
  }, []);

  useEffect(() => {
    if (!activo) return;
    arranco.current = true;
    if (menos) {
      setValor(fin);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const paso = (ahora: number) => {
      const p = Math.min(1, (ahora - t0) / duracion);
      const suave = 1 - Math.pow(1 - p, 4);
      setValor(fin * suave);
      if (p < 1) raf = requestAnimationFrame(paso);
    };
    raf = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(raf);
  }, [activo, menos, fin, duracion]);

  return valor;
}

/* ---------- Piezas ---------- */

function Fondo() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_0%,var(--bg-2)_0%,var(--bg)_65%)]" />
      <div className="absolute -left-40 top-[8%] size-[36rem] rounded-full bg-accent/[0.06] blur-3xl" />
      <div className="absolute -right-48 bottom-[-18%] size-[44rem] rounded-full bg-water/[0.16] blur-3xl" />
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgb(255 255 255 / 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgb(255 255 255 / 0.05) 1px, transparent 1px)",
          backgroundSize: "56px 56px",
          maskImage: "radial-gradient(70% 60% at 50% 40%, black, transparent)",
          WebkitMaskImage: "radial-gradient(70% 60% at 50% 40%, black, transparent)",
        }}
      />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />
    </div>
  );
}

function Copiar({ texto }: { texto: string }) {
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    if (!copiado) return;
    const id = window.setTimeout(() => setCopiado(false), 2200);
    return () => window.clearTimeout(id);
  }, [copiado]);

  /** Respaldo sin Clipboard API: devuelve el foco a donde estaba la persona. */
  function copiarRespaldo(): boolean {
    const previo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const area = document.createElement("textarea");
    area.value = texto;
    area.setAttribute("readonly", "");
    area.setAttribute("aria-hidden", "true");
    area.style.position = "fixed";
    area.style.top = "0";
    area.style.left = "0";
    area.style.opacity = "0";
    document.body.appendChild(area);
    let ok = false;
    try {
      area.select();
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    area.remove();
    previo?.focus({ preventScroll: true });
    return ok;
  }

  async function copiar() {
    let ok = false;
    try {
      if (!navigator.clipboard) throw new Error("sin portapapeles");
      await navigator.clipboard.writeText(texto);
      ok = true;
    } catch {
      ok = copiarRespaldo();
    }
    if (ok) setCopiado(true);
  }

  const Icono = copiado ? Check : Copy;
  return (
    <>
      <button
        type="button"
        onClick={copiar}
        aria-label={t.copiarLector}
        className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-[color,background-color,border-color,scale] duration-150 ease-[var(--ease-out)] motion-safe:active:scale-[0.97] ${
          copiado
            ? "border-ok/40 bg-ok-bg text-ok"
            : "border-line bg-surface text-ink-2 hover:bg-surface-2 hover:text-ink"
        }`}
      >
        <Icono aria-hidden className="size-3.5 animate-[icono_180ms_var(--ease-out)]" strokeWidth={2.25} />
        <span aria-hidden>{copiado ? t.copiado : t.copiarId}</span>
      </button>
      <span role="status" className="sr-only">
        {copiado ? t.copiadoLector : ""}
      </span>
    </>
  );
}

function Apoyo({
  icono: Icono,
  valor,
  texto,
  color,
  className = "",
}: {
  icono: typeof Droplets;
  className?: string;
  valor: string;
  texto: string;
  color: string;
}) {
  return (
    <div className={`glass flex h-full min-w-0 flex-col rounded-2xl p-3 sm:rounded-3xl sm:p-4 ${className}`}>
      <p className="flex items-center gap-2">
        <span
          className={`inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-white/[0.06] ring-1 ring-line sm:size-7 ${color}`}
        >
          <Icono aria-hidden className="size-3.5 sm:size-4" strokeWidth={2} />
        </span>
        <span className="whitespace-nowrap font-mono text-lg font-semibold tracking-tight text-ink tabular-nums sm:text-2xl">
          {valor}
        </span>
      </p>
      <p className="mt-1.5 text-xs leading-snug text-ink-2 sm:mt-2 sm:text-sm">{texto}</p>
    </div>
  );
}

/* ---------- Hipótesis física: seco → mojado → con agua ---------- */

type ClavePaso = (typeof t.hipotesis.pasos)[number]["clave"];

/** Ícono, flecha, color y alto de la barrita de eco de cada paso (normal / sube / cae). */
const PASO: Record<ClavePaso, { icono: typeof Sun; flecha: typeof Minus; color: string; barra: string; alto: string }> = {
  seco: { icono: Sun, flecha: Minus, color: "text-ink-2", barra: "bg-ink-2/70", alto: "h-1/2" },
  mojado: { icono: Droplets, flecha: ArrowUp, color: "text-accent", barra: "bg-accent", alto: "h-[90%]" },
  agua: { icono: Waves, flecha: ArrowDown, color: "text-[#5ea2ea]", barra: "bg-water", alto: "h-[15%]" },
};

function Hipotesis() {
  const h = t.hipotesis;
  return (
    <section aria-labelledby="s5-hipotesis" className="glass rounded-2xl p-3 sm:rounded-[1.75rem] sm:p-4">
      <div className="grid gap-3 lg:grid-cols-12 lg:items-center lg:gap-5">
        <div className="lg:col-span-7">
          <p className="flex items-center gap-2 font-mono text-[11px] tracking-[0.14em] text-accent uppercase">
            {h.etiqueta}
            <span aria-hidden className="text-ink-3">·</span>
            <span id="s5-hipotesis" className="normal-case tracking-normal text-ink-2">
              {h.titulo}
            </span>
          </p>
          {/* Los 3 pasos en 3 columnas. En el celular solo ícono, nombre y eco (la frase de al lado explica). */}
          <ol className="mt-2 grid grid-cols-3 gap-1.5 sm:mt-3 sm:gap-3">
            {h.pasos.map((p, i) => {
              const { icono: Icono, flecha: Flecha, color, barra, alto } = PASO[p.clave];
              return (
                <li
                  key={p.clave}
                  className="flex flex-col items-center gap-1.5 rounded-xl border border-line bg-bg/40 px-1.5 py-2 text-center sm:items-start sm:p-3 sm:text-left lg:flex-row lg:items-start lg:gap-2.5 lg:px-3 lg:py-2.5"
                >
                  <div className="flex shrink-0 items-center gap-2">
                    {/* Barrita del eco: alta, media o casi nada. Solo apoyo visual: el texto dice lo mismo. */}
                    <span aria-hidden className="flex h-7 w-2 items-end overflow-hidden rounded-full bg-white/[0.06]">
                      <span className={`w-full rounded-full ${barra} ${alto}`} />
                    </span>
                    <span className={`inline-flex size-7 items-center justify-center rounded-full bg-white/[0.06] ring-1 ring-line ${color}`}>
                      <Icono aria-hidden className="size-4" strokeWidth={2} />
                    </span>
                  </div>
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-baseline justify-center gap-x-1.5 text-sm font-semibold text-ink sm:justify-start">
                      <span className="font-mono text-xs text-ink-3 max-sm:hidden">{i + 1}.</span>
                      {p.nombre}
                      <span className={`inline-flex basis-full items-center justify-center gap-0.5 text-xs font-medium sm:basis-auto sm:justify-start lg:basis-full ${color}`}>
                        <Flecha aria-hidden className="size-3.5" strokeWidth={2.5} />
                        {p.eco}
                      </span>
                    </p>
                    <p className="text-xs leading-snug text-ink-2 max-sm:hidden">{p.texto}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
        <p className="text-pretty text-xs leading-relaxed text-ink-2 sm:text-sm lg:col-span-5">
          <span className="max-sm:hidden">{h.fraseCausa} </span>
          {h.fraseComo}
        </p>
      </div>
    </section>
  );
}

/* ---------- Sección ---------- */

export default function Seccion5() {
  const menos = useMenosMovimiento();
  const refNumero = useRef<HTMLElement>(null);
  const activo = useAlEntrar(refNumero);
  const contado = useContador(subidaDb, activo, menos);

  return (
    // Abajo deja lugar para el camino del cierre (Final).
    <Seccion id="s5" titulo={t.tituloSeccion} className="pb-[195px]! sm:pb-[245px]! lg:pb-[305px]!">
      <Fondo />
      <Final />

      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 sm:gap-5 lg:gap-4">
        {/* Encabezado */}
        <Reveal>
          <header className="max-w-3xl">
            <Encabezado titulo={t.titulo} />
            <p className="mt-2 text-pretty text-sm text-ink-2 sm:mt-4 sm:text-lg lg:mt-2">{t.bajada}</p>
          </header>
        </Reveal>

        {/* Primero la causa (hipótesis), después la prueba (el número medido). */}
        <Reveal delay={30}>
          <Hipotesis />
        </Reveal>

        <div className="grid gap-3 sm:gap-4 lg:grid-cols-12 lg:gap-5">
          {/* Número grande: lo que el radar midió (el eco sube sobre los caminos de tierra y su entorno). Sin km "intransitables":
              salían de una sospecha, no de un corte confirmado (docs/hipotesis-fisica.md). */}
          <Reveal delay={50} className="lg:col-span-7">
            <article
              ref={refNumero}
              className="glass relative flex h-full flex-col justify-center overflow-hidden rounded-[1.75rem] p-4 sm:p-8 lg:p-6"
            >
              <div
                aria-hidden
                className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-water/20 blur-3xl"
              />
              <div>
                <Estado tono="mojado" texto={t.estado} grande />
              </div>
              <p className="sr-only">{t.lectorPrincipal(fmt(subidaDb, DECIMALES_DB), fmt(medicion.km_tierra, 1))}</p>
              <div aria-hidden className="mt-3 flex flex-wrap items-end gap-x-3 gap-y-2 sm:mt-6 lg:mt-4">
                {/* El valor final, invisible, reserva el ancho: el rótulo no salta mientras sube el contador. */}
                <span className="grid text-[clamp(3.75rem,16vw,7.5rem)] font-semibold leading-[0.85] tracking-[-0.04em] text-ink tabular-nums">
                  <span className="invisible col-start-1 row-start-1">{t.ecoValor(fmt(subidaDb, DECIMALES_DB))}</span>
                  <span className="col-start-1 row-start-1">{t.ecoValor(fmt(contado, DECIMALES_DB))}</span>
                </span>
                <span className="pb-1 text-lg leading-tight text-ink-2 sm:pb-2 sm:text-2xl">
                  {t.unidadDb}
                  <br />
                  <span className="whitespace-nowrap text-accent">{t.ecoRotulo}</span>
                </span>
              </div>
              <p aria-hidden className="mt-3 text-pretty text-base font-medium leading-snug text-ink sm:mt-6 sm:text-xl lg:mt-4">
                {t.principal}
              </p>
              <p className="mt-2 text-pretty text-xs text-ink-3 sm:text-sm">
                {t.detallePrincipal(fmt(medicion.km_tierra, 1))}
              </p>

            </article>
          </Reveal>

          <div className="flex flex-col gap-3 sm:gap-4 lg:col-span-5">
            {/* Datos de apoyo: 2 columnas compactas también en el celular */}
            <Reveal delay={90}>
              <div className="grid grid-cols-2 gap-3 sm:gap-4">
                <Apoyo
                  icono={TrendingUp}
                  color="text-accent"
                  valor={t.subenValor(fmt(subenDeCada10, 0))}
                  texto={t.subenTexto(fmt(abierta.campo_db, 2), fmt(abierta.eje_db, 2))}
                />
                <Apoyo
                  icono={Waves}
                  color="text-accent"
                  valor={t.aguaValor(fmt(agua.pct_con_agua, decimalesAgua))}
                  texto={t.aguaTexto(fmt(agua.pixeles_con_agua, 0), fmt(medicion.pixeles_eje, 0))}
                />
              </div>
            </Reveal>

            {/* Fuente */}
            <Reveal delay={120} className="flex-1">
              <section aria-labelledby="s5-fuente" className="glass h-full rounded-2xl p-3 sm:rounded-[1.75rem] sm:p-5">
                <div className="hidden items-center gap-2 sm:flex">
                  <Satellite aria-hidden className="size-4 text-accent" strokeWidth={2} />
                  <h3 id="s5-fuente" className="text-sm font-medium text-ink-2">
                    {t.tituloFuente}
                  </h3>
                </div>
                <p className="mt-2 hidden font-mono text-xs leading-relaxed text-ink sm:block">{t.lineaFuente(radar)}</p>
                <p className="mt-1 hidden font-mono text-xs leading-relaxed text-ink-2 sm:block">{t.medicion}</p>
                <div className="flex flex-wrap items-center justify-between gap-2 sm:mt-3">
                  <p className="text-sm font-medium text-accent">
                    <Fuente href={radar.verificar_url}>
                      {t.verificar}
                      <span className="sr-only"> {t.nuevaPestana}</span>
                    </Fuente>
                  </p>
                  <Copiar texto={radar.archivo} />
                </div>
              </section>
            </Reveal>
          </div>
        </div>

        {/* Cierre + pie */}
        <Reveal delay={150}>
          <footer className="flex flex-col gap-3 border-t border-line pt-3 sm:gap-5 sm:pt-4 lg:flex-row lg:items-end lg:justify-between lg:gap-10">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between lg:order-last lg:flex-col lg:items-end">
              {/* Sin botón "Probá la demo" (pedido de Facundo, 15/11). */}
              <p className="text-base font-medium text-ink">{t.cierre}</p>
              <p className="hidden items-baseline gap-2 sm:flex">
                <span className="text-sm font-semibold tracking-[0.32em] text-ink">{t.marca}</span>
                <span className="text-xs text-ink-3">{t.marcaBajada}</span>
              </p>
            </div>

            <div className="flex max-w-3xl flex-col gap-1.5 text-xs leading-relaxed text-ink-3">
              <p>
                <span className="mr-1.5 inline-flex items-center gap-1 font-semibold text-ok">
                  <Check aria-hidden className="size-3.5" strokeWidth={2.5} />
                  {t.real}
                </span>
                {t.realTexto}{" "}
                <span className="ml-1 mr-1.5 inline-flex items-center gap-1 font-semibold text-warn">
                  <FlaskConical aria-hidden className="size-3.5" strokeWidth={2.25} />
                  {t.simulado}
                </span>
                {t.simuladoTexto}
              </p>
              <p className="hidden sm:block">
                {t.hecho}
                <span aria-hidden className="mx-2 text-ink-3/60">
                  {t.separador}
                </span>
                {t.ia}
              </p>
            </div>
          </footer>
        </Reveal>
      </div>
    </Seccion>
  );
}
