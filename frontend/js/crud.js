/* Controlador de formularios y tablas. Las lecturas y escrituras pasan por la API. */
(function (H) {
  "use strict";
  H.crud = function (config) {
    H.ui.iniciar(async function () {
      var ui = H.ui, api = H.api;
      var formulario = document.getElementById(config.formulario);
      var tabla = document.getElementById(config.tabla);
      var guardar = formulario.querySelector('[type="submit"]');
      var limpiar = formulario.querySelector('[type="reset"]');
      var etiquetaGuardar = guardar.innerHTML;
      var etiquetaLimpiar = limpiar.innerHTML;
      var editando = null;
      var carga = 0;
      var avisoEdicion = document.createElement("p");
      avisoEdicion.className = "alerta info";
      avisoEdicion.setAttribute("role", "status");
      formulario.prepend(avisoEdicion);

      async function cargar() {
        var turno = ++carga;
        tabla.setAttribute("aria-busy", "true");
        try {
          if (config.preparar) await config.preparar();
          var registros = await api.listar(config.coleccion, config.filtros ? config.filtros() : {});
          if (turno !== carga) return;
          var filas = registros.map(function (registro) {
            var acciones = '<td class="num"><button class="btn secundario chico" data-editar="' +
              ui.escapar(registro.id) + '">Editar</button> <button class="btn secundario chico" data-eliminar="' +
              ui.escapar(registro.id) + '">Eliminar</button></td>';
            return "<tr>" + config.celdas(registro) + acciones + "</tr>";
          });
          ui.pintarTabla(config.tabla, filas, config.columnas, "No hay registros que coincidan.");
          ui.contador(config.contador, registros.length, config.singular, config.plural);
        } finally {
          if (turno === carga) tabla.setAttribute("aria-busy", "false");
        }
      }

      formulario.addEventListener("reset", function () {
        editando = null;
        guardar.innerHTML = etiquetaGuardar;
        limpiar.innerHTML = etiquetaLimpiar;
        avisoEdicion.className = "alerta info";
        ui.limpiarErrores(formulario);
        ui.ocultarAviso();
      });

      formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();
        if (formulario.dataset.procesando) return;
        ui.limpiarErrores(formulario);
        var datos = {};
        config.campos.forEach(function (campo) { datos[campo] = document.getElementById(campo).value.trim(); });
        var id = editando;
        ui.ejecutar(formulario, async function () {
          await api.guardar(config.coleccion, datos, id);
          formulario.reset();
          if (datos.centroId) document.getElementById("centroId").value = datos.centroId;
          ui.aviso(id ? "Registro actualizado correctamente." : "Registro guardado correctamente.", "ok");
          try { await cargar(); }
          catch (error) { throw new Error("El registro se guardó, pero la lista no pudo actualizarse. Recarga la página."); }
        });
      });

      tabla.addEventListener("click", function (evento) {
        if (formulario.dataset.procesando) return;
        var boton = evento.target.closest("[data-editar], [data-eliminar]");
        if (!boton) return;
        var id = boton.getAttribute("data-editar") || boton.getAttribute("data-eliminar");
        if (boton.hasAttribute("data-eliminar")) {
          var mensaje = "¿Eliminar este registro?";
          if (config.coleccion === "centros") mensaje += " También se eliminarán las áreas de este centro.";
          if (!confirm(mensaje)) return;
          ui.ejecutar(formulario, async function () {
            await api.eliminar(config.coleccion, id);
            if (editando === id) formulario.reset();
            ui.aviso("Registro eliminado correctamente.", "info");
            await cargar();
          });
        } else {
          ui.ejecutar(formulario, async function () {
            var registro = await api.obtener(config.coleccion, id);
            config.campos.forEach(function (campo) { document.getElementById(campo).value = registro[campo]; });
            editando = id;
            guardar.textContent = "Actualizar " + config.singular;
            limpiar.textContent = "Cancelar edición";
            ui.limpiarErrores(formulario);
            avisoEdicion.textContent = "Editando: " + (registro.nombres || registro.nombre);
            avisoEdicion.className = "alerta visible info";
            formulario.scrollIntoView({behavior: "smooth", block: "center"});
          });
        }
      });

      var filtro = document.getElementById("filtro");
      if (filtro) {
        var temporizador;
        filtro.addEventListener(filtro.matches("select") ? "change" : "input", function () {
          clearTimeout(temporizador);
          temporizador = setTimeout(function () { cargar().catch(function (error) { ui.aviso(error.message, "error"); }); }, 200);
        });
      }
      await ui.ejecutar(formulario, cargar, true);
    });
  };
})(window.Hospital);
