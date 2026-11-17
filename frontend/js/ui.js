/* ============================================================
   modulo: interfaz
   Utilidades comunes: navegación activa, mensajes, tablas,
   formato de fechas y validaciones sencillas.
   ============================================================ */

window.Hospital = window.Hospital || {};

(function (H) {
  "use strict";

  var ui = {

    iniciar: function (accion) {
      async function ejecutar() {
        try { await accion(); }
        catch (error) {
          var aviso = document.createElement("div");
          aviso.className = "alerta visible error";
          aviso.setAttribute("role", "alert");
          aviso.textContent = error.message + " Recarga la página para reintentar.";
          document.querySelector("main").prepend(aviso);
        }
      }
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ejecutar);
      else ejecutar();
    },

    /* ---------- navegación ---------- */

    /** Marca el enlace del menú que corresponde a la página abierta */
    marcarNavegacion: function () {
      var pagina = (location.pathname.split("/").pop() || "index.html").toLowerCase();
      var enlaces = document.querySelectorAll(".nav a");
      for (var i = 0; i < enlaces.length; i++) {
        var destino = enlaces[i].getAttribute("href").toLowerCase();
        if (destino === pagina) enlaces[i].className = "activo";
      }
    },

    /* ---------- mensajes ---------- */

    /** Muestra un aviso: tipo ok | error | info */
    aviso: function (texto, tipo) {
      var caja = document.getElementById("aviso");
      if (!caja) return;
      caja.className = "alerta visible " + (tipo || "info");
      caja.textContent = texto;
      clearTimeout(caja._t);
      caja._t = setTimeout(function () {
        caja.className = "alerta " + (tipo || "info");
      }, 6000);
    },

    ocultarAviso: function () {
      var caja = document.getElementById("aviso");
      if (caja) caja.className = "alerta";
    },

    /** Evita envíos duplicados y muestra los errores reales del servidor. */
    ejecutar: async function (elemento, accion, propagar) {
      var controles = elemento.matches("button") ? [elemento] :
        Array.from(elemento.querySelectorAll("button, input, select"));
      if (elemento.dataset.procesando) return;
      elemento.dataset.procesando = "1";
      var previos = controles.map(function (control) { return control.disabled; });
      controles.forEach(function (control) { control.disabled = true; });
      try {
        await accion();
      } catch (error) {
        if (error.campo) ui.error(error.campo, error.message);
        ui.aviso(error.message || "No se pudo completar la operación.", "error");
        if (propagar) throw error;
      } finally {
        controles.forEach(function (control, indice) { control.disabled = previos[indice]; });
        delete elemento.dataset.procesando;
      }
    },

    /** Escribe el error debajo de un campo (id + "Error") */
    error: function (campoId, mensaje) {
      var campo = document.getElementById(campoId);
      var hueco = document.getElementById(campoId + "Error");
      if (campo) campo.classList.toggle("invalido", !!mensaje);
      if (hueco) hueco.textContent = mensaje || "";
      return !mensaje;
    },

    limpiarErrores: function (form) {
      var invalidos = form.querySelectorAll(".invalido");
      for (var i = 0; i < invalidos.length; i++) invalidos[i].classList.remove("invalido");
      var errores = form.querySelectorAll(".error");
      for (var j = 0; j < errores.length; j++) errores[j].textContent = "";
    },

    /* ---------- formato ---------- */

    escapar: function (texto) {
      return String(texto == null ? "" : texto)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    },

    /** Texto comparable: sin mayúsculas ni tildes */
    normalizar: function (texto) {
      return String(texto == null ? "" : texto)
        .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .toLowerCase().trim();
    },

    /** "1992-04-18" -> "18/04/1992" */
    fecha: function (iso) {
      if (!iso) return "—";
      var p = String(iso).split("-");
      if (p.length !== 3) return iso;
      return p[2] + "/" + p[1] + "/" + p[0];
    },

    /** Edad en años a partir de la fecha de nacimiento */
    edad: function (iso) {
      if (!iso) return "—";
      var n = new Date(iso + "T00:00:00");
      if (isNaN(n.getTime())) return "—";
      var hoy = new Date();
      var edad = hoy.getFullYear() - n.getFullYear();
      var m = hoy.getMonth() - n.getMonth();
      if (m < 0 || (m === 0 && hoy.getDate() < n.getDate())) edad--;
      return edad >= 0 ? edad + " años" : "—";
    },

    /** Etiqueta de color según el nivel de triaje */
    triaje: function (valor) {
      if (!valor) return '<span class="tag sin">Sin asignar</span>';
      var clase = { "Nivel I": "n1", "Nivel II": "n2", "Nivel III": "n3", "Nivel IV": "n4" }[valor] || "sin";
      return '<span class="tag ' + clase + '">' + ui.escapar(valor) + "</span>";
    },

    /** Cédula ecuatoriana: 10 dígitos */
    cedulaValida: function (valor) {
      return /^\d{10}$/.test(String(valor || "").trim());
    },

    /** Teléfono: 7 a 10 dígitos */
    telefonoValido: function (valor) {
      return /^\d{7,10}$/.test(String(valor || "").trim());
    },

    /* ---------- tablas ---------- */

    /** Pinta filas en el tbody de una tabla; filas vacías muestran un mensaje */
    pintarTabla: function (tbodyId, filas, columnas, mensajeVacio) {
      var cuerpo = document.getElementById(tbodyId);
      if (!cuerpo) return;
      if (!filas.length) {
        cuerpo.innerHTML = '<tr><td class="vacio" colspan="' + columnas + '">' +
          ui.escapar(mensajeVacio || "Todavía no hay registros.") + "</td></tr>";
        return;
      }
      cuerpo.innerHTML = filas.join("");
    },

    /** Cuenta los registros y lo muestra en un elemento */
    contador: function (elementoId, total, singular, plural) {
      var el = document.getElementById(elementoId);
      if (!el) return;
      el.textContent = total + " " + (total === 1 ? singular : plural);
    },

    /** Convierte "2026-11-13" en objeto Date local seguro */
    aFecha: function (iso) {
      return new Date(String(iso) + "T00:00:00");
    }
  };

  H.ui = ui;

  document.addEventListener("DOMContentLoaded", function () {
    ui.marcarNavegacion();
    var anio = document.getElementById("anio");
    if (anio) anio.textContent = new Date().getFullYear();
  });
})(window.Hospital);
