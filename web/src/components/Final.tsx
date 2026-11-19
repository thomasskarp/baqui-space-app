// Cierre de la página, al pie de la sección 5 (va adentro, así comparte su fondo y no queda costura):
// una foto real de un camino rural inundado, pasada al azul de noche de la página.
// Foto: "Camino inundado en Salinas, Alvarado, Veracruz 01", de Isaacvp, Wikimedia Commons, CC BY-SA 4.0.
// Adaptada (recorte y tono) con la misma licencia. Es ilustrativa: no es el corredor medido.

const FUENTE = "https://commons.wikimedia.org/wiki/File:Camino_inundado_en_Salinas,_Alvarado,_Veracruz_01.jpg";

export default function Final() {
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 h-[175px] overflow-hidden sm:h-[225px] lg:h-[275px]">
      {/* eslint-disable-next-line @next/next/no-img-element -- imagen estática ya optimizada (webp, dos tamaños) */}
      <img
        src="/camino-inundado.webp"
        srcSet="/camino-inundado-1200.webp 1200w, /camino-inundado.webp 2400w"
        sizes="100vw"
        alt=""
        aria-hidden
        loading="lazy"
        decoding="async"
        // La foto se funde con el cielo de la página (máscara: sirve sobre cualquier color de fondo).
        className="absolute inset-0 h-full w-full object-cover object-[50%_45%] [mask-image:linear-gradient(180deg,transparent_0%,rgb(0_0_0/0.35)_25%,#000_60%)]"
      />
      <a
        href={FUENTE}
        target="_blank"
        rel="noopener noreferrer"
        className="pointer-events-auto absolute right-2 bottom-1.5 text-[11px] text-white/70 hover:text-white sm:right-3 sm:bottom-2"
      >
        Foto ilustrativa: Isaacvp, Wikimedia Commons, CC BY-SA 4.0 (adaptada)
      </a>
    </div>
  );
}
