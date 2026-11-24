/* Cliente HTTP. No almacena registros ni simula operaciones de la base de datos. */
window.Hospital = window.Hospital || {};
(function (H) {
  "use strict";
  async function solicitar(ruta, opciones) {
    if (location.protocol === "file:") {
      throw new Error("Inicia el programa con INICIAR.cmd o Hospital.exe.");
    }
    var respuesta;
    var control = new AbortController();
    // Límite de 15 s: si el backend no responde, la interfaz no queda esperando.
    var limite = setTimeout(function () { control.abort(); }, 15000);
    try {
      respuesta = await fetch("/api" + ruta, Object.assign({cache: "no-store", signal: control.signal}, opciones));
      // DELETE responde 204 sin cuerpo: no hay JSON que leer.
      if (respuesta.status === 204) return null;
      var contenido = await respuesta.json();
      if (!respuesta.ok) {
        var fallo = new Error(contenido.error || "No se pudo completar la operación.");
        fallo.campo = contenido.campo;
        fallo.estado = respuesta.status;
        throw fallo;
      }
      return contenido;
    } catch (error) {
      if (error.estado) throw error;
      throw new Error("No se pudo conectar con el backend. Comprueba que el programa siga abierto y reintenta.");
    } finally {
      clearTimeout(limite);
    }
  }
  function ruta(coleccion, id) {
    return "/" + encodeURIComponent(coleccion) + (id ? "/" + encodeURIComponent(id) : "");
  }
  H.api = {
    listar: async function (coleccion, filtros) {
      var parametros = new URLSearchParams(filtros || {});
      return (await solicitar(ruta(coleccion) + "?" + parametros)).registros;
    },
    obtener: async function (coleccion, id) {
      return (await solicitar(ruta(coleccion, id))).registro;
    },
    guardar: async function (coleccion, registro, id) {
      return (await solicitar(ruta(coleccion, id), {
        method: id ? "PUT" : "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(registro)
      })).registro;
    },
    eliminar: function (coleccion, id) { return solicitar(ruta(coleccion, id), {method: "DELETE"}); },
    resumen: function () { return solicitar("/resumen"); },
    disponibilidad: function (filtros) {
      return solicitar("/disponibilidad?" + new URLSearchParams(filtros || {}));
    }
  };
})(window.Hospital);
