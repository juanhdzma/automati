// Widget de Scriptable: dias que faltan para el proximo pago.
//
// Como usarlo: en la app de Scriptable, creas un script nuevo, pegas este
// archivo tal cual, y lo agregas como widget de home screen (tamaño chico).
// Solo funciona si el iPhone puede llegarle a Automati -- si estas fuera de
// la red donde resuelve automati.nufi.com.co, el widget muestra "sin conexion"
// en vez de romperse.

const AUTOMATI_URL = "https://automati.nufi.com.co"

const BG = "#16181d"
const ACCENT = "#34c759"
const TEXT_MUTED = "#8b8f98"

async function getPayday() {
  const req = new Request(`${AUTOMATI_URL}/scriptable-ios/payday`)
  req.timeoutInterval = 8
  return await req.loadJSON()
}

// Traduce dias_left a lo que se ve: 0 y 1 son casos especiales en texto, el
// resto es "X dias" + "para el pago". Separado de buildWidget para poder
// testearlo a mano sin tocar la red (correr esta funcion sola con distintos
// valores).
function headlineFor(daysLeft) {
  if (daysLeft === 0) return { headline: "Hoy", subtitle: "te pagan" }
  if (daysLeft === 1) return { headline: "Mañana", subtitle: "te pagan" }
  return { headline: `${daysLeft} días`, subtitle: "para el pago" }
}

function buildWidget(data) {
  const widget = new ListWidget()
  widget.backgroundColor = new Color(BG)
  widget.setPadding(16, 16, 16, 16)

  const { headline, subtitle } = data.error
    ? { headline: "--", subtitle: "sin conexion" }
    : headlineFor(data.days_left)

  // Header chico: icono + label de contexto en mayusculas, como en los
  // widgets nativos de Apple (Stocks, Weather). Le da un lugar al icono sin
  // competir en tamaño con el headline, y explica que es el numero de abajo.
  const header = widget.addStack()
  header.centerAlignContent()

  const icon = header.addImage(SFSymbol.named("banknote.fill").image)
  icon.imageSize = new Size(12, 12)
  icon.tintColor = new Color(ACCENT)

  header.addSpacer(4)

  const eyebrow = header.addText("PROXIMO PAGO")
  eyebrow.font = Font.mediumSystemFont(10)
  eyebrow.textColor = new Color(TEXT_MUTED)

  // Spacers flexibles arriba y abajo del bloque central: lo centran
  // verticalmente en el espacio libre, en vez de dejarlo pegado arriba con
  // aire suelto abajo (o un hueco raro en el medio).
  widget.addSpacer()

  const headlineText = widget.addText(headline)
  headlineText.font = Font.boldSystemFont(26)
  headlineText.textColor = new Color(ACCENT)

  widget.addSpacer(2)

  const subtitleText = widget.addText(subtitle)
  subtitleText.font = Font.mediumSystemFont(12)
  subtitleText.textColor = new Color(TEXT_MUTED)

  widget.addSpacer()

  // Linea separadora fina antes de la fecha: le da estructura al footer en
  // vez de dejarlo flotando suelto. Ancho 0 = ocupa todo el ancho disponible.
  const divider = widget.addStack()
  divider.size = new Size(0, 1)
  divider.backgroundColor = new Color(TEXT_MUTED, 0.25)

  widget.addSpacer(8)

  const date = widget.addText(data.error ? "" : data.next_payday)
  date.font = Font.systemFont(11)
  date.textColor = new Color(TEXT_MUTED)

  // iOS decide cuando refresca de verdad; esto es un pedido, no una garantia.
  widget.refreshAfterDate = new Date(Date.now() + 30 * 60 * 1000)
  return widget
}

let data
try {
  data = await getPayday()
} catch (e) {
  data = { error: true }
}

const widget = buildWidget(data)

if (config.runsInWidget) {
  Script.setWidget(widget)
} else {
  await widget.presentSmall()
}
Script.complete()
