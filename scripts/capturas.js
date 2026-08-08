/* Lleva la aplicación al estado que se quiere retratar.
 *
 * Se evalúa DENTRO de la página. El tablero se alimenta de un MJPEG —una
 * respuesta que no termina nunca— así que la página jamás queda «cargada» y
 * las esperas tienen que ser de tiempo real, no de tiempo virtual.
 */
(() => {
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms))
  const $ = (id) => document.getElementById(id)

  async function hasta(fn, ms = 60000, cada = 200) {
    const fin = Date.now() + ms
    for (;;) {
      let v
      try { v = fn() } catch (e) { v = null }
      if (v) return v
      if (Date.now() > fin) throw new Error('se agotó la espera')
      await esperar(cada)
    }
  }

  async function elegirVideo(op) {
    const sel = await hasta(() => {
      const s = $('videoSelect')
      return s && s.options.length && s.options[0].value ? s : null
    })
    /* El init() de la app elige el primer video por su cuenta y carga su
       frame. Seleccionar otro antes de que acabe pierde la carrera: la
       captura sale con el video equivocado. Pasó exactamente eso. */
    await hasta(() => {
      const img = $('frameImg')
      return img && (img.naturalWidth > 0 || img.getAttribute('src'))
    }, 60000).catch(() => {})
    await esperar(800)

    const re = new RegExp(op.video || '.', 'i')
    const elegida = [...sel.options].find((o) => re.test(o.value))
    if (!elegida) throw new Error('ningún video casa con ' + op.video)
    sel.value = elegida.value
    sel.dispatchEvent(new Event('change', { bubbles: true }))
    await esperar(3500)
    if (sel.value !== elegida.value) throw new Error('el video no se fijó')
  }

  function modulo(op) {
    if (!op.uc) return
    const b = [...document.querySelectorAll('.uc')]
      .find((x) => x.dataset.uc === op.uc)
    if (!b) throw new Error('no existe el módulo ' + op.uc)
    b.click()
  }

  const ESCENAS = {
    /* Recién abierto: el editor sobre el primer frame, sin procesar.
       Es lo primero que ve cualquiera y enseña que las zonas se dibujan. */
    async editor(op) {
      await elegirVideo(op)
      modulo(op)
      await esperar(2000)
    },

    /* En marcha: video anotado a la izquierda, cifras vivas a la derecha. */
    async tablero(op) {
      await elegirVideo(op)
      modulo(op)
      await esperar(1500)
      $('startBtn').click()
      await hasta(() => $('stream') && $('stream').naturalWidth > 0, 120000)
      await esperar((op.segs || 25) * 1000)
    },
  }

  window.montar = async (nombre, op) => {
    const fn = ESCENAS[nombre]
    if (!fn) throw new Error('escena desconocida: ' + nombre)
    /* Una captura anterior pudo dejar el procesador en marcha; entonces
       /api/start responde con error, el stream nunca recibe src, y la espera
       se agota sin decir por qué. Se para siempre antes de empezar. */
    await fetch('/api/stop', { method: 'POST' }).catch(() => {})
    await esperar(1500)
    await fn(op || {})
    // Las tarjetas entran con una animación de opacidad; disparar la captura
    // en mitad de ella deja el tablero con pinta de cargado a medias.
    await esperar(1200)
    return 'ok'
  }
})()
