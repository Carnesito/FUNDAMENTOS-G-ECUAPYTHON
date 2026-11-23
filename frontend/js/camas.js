/* Habitaciones, camas y disponibilidad: todo se consulta en el backend. */
(function (H) {
  "use strict";
  var ui = H.ui, api = H.api;
  var datos = {
    centros: [], areas: [], pacientes: [], habitaciones: [], habitacionesTodas: [],
    camas: [], disponibilidad: null
  };
  var editandoHabitacion = null, editandoCama = null;

  function el(id) { return document.getElementById(id); }
  function valor(id) { return el(id).value.trim(); }
  function centroDeArea(area) {
    return datos.centros.filter(function (c) { return c.id === area.centroId; })[0];
  }

  function llenar(select, lista, etiqueta, valorActual) {
    var anterior = valorActual || select.value;
    select.innerHTML = '<option value="">' + ui.escapar(etiqueta) + "</option>" + lista.map(function (item) {
      return '<option value="' + ui.escapar(item.valor) + '">' + ui.escapar(item.texto) + "</option>";
    }).join("");
    select.value = lista.some(function (item) { return item.valor === anterior; }) ? anterior : "";
  }

  function llenarSelectores() {
    var centroFiltro = el("filtroCentro").value, areaFiltro = el("filtroArea").value;
    var areasFiltradas = datos.areas.filter(function (a) {
      return !centroFiltro || a.centroId === centroFiltro;
    });
    llenar(el("filtroCentro"), datos.centros.map(function (c) {
      return {valor: c.id, texto: c.nombre};
    }), "Todos los centros", centroFiltro);
    llenar(el("filtroArea"), areasFiltradas.map(function (a) {
      var centro = centroDeArea(a);
      return {valor: a.id, texto: (centro ? centro.nombre + " · " : "") + a.nombre};
    }), "Todas las áreas", areaFiltro);
    llenar(el("areaId"), datos.areas.map(function (a) {
      var centro = centroDeArea(a);
      return {valor: a.id, texto: (centro ? centro.nombre + " · " : "") + a.nombre};
    }), "Selecciona un área");
    llenar(el("habitacionId"), datos.habitacionesTodas.map(function (h) {
      return {valor: h.id, texto: h.areaNombre + " · Habitación " + h.numero + " (piso " + h.piso + ")"};
    }), "Selecciona una habitación");
    el("sinAreas").style.display = datos.areas.length ? "none" : "block";
    el("formHabitacion").style.display = datos.areas.length ? "" : "none";
    el("sinHabitaciones").style.display = datos.habitacionesTodas.length ? "none" : "block";
    el("formCama").style.display = datos.habitacionesTodas.length ? "" : "none";
  }

  function estadoCama(estado) {
    var clase = {"Disponible": "cama-disponible", "Ocupada": "cama-ocupada",
                 "Mantenimiento": "cama-mantenimiento"}[estado] || "sin";
    return '<span class="tag ' + clase + '">' + ui.escapar(estado) + "</span>";
  }

  function pintarDisponibilidad() {
    var info = datos.disponibilidad || {centros: [], totales: {}};
    var totales = info.totales || {};
    el("dispoCifras").innerHTML = [
      [totales.total || 0, "camas totales"], [totales.disponibles || 0, "disponibles"],
      [totales.ocupadas || 0, "ocupadas"], [totales.mantenimiento || 0, "mantenimiento"]
    ].map(function (par) {
      return '<span class="dispo-cifra"><b>' + par[0] + "</b>" + ui.escapar(par[1]) + "</span>";
    }).join("");
    el("contadorDisponibles").textContent = (totales.disponibles || 0) + " camas libres";
    if (!info.centros.length) {
      el("disponibilidad").innerHTML = '<div class="vacio-estado">Sin centros médicos registrados.</div>';
      return;
    }
    el("disponibilidad").innerHTML = info.centros.map(function (centro) {
      var areas = centro.areas.length ? centro.areas.map(function (area) {
        var porcentaje = area.total ? Math.round(area.disponibles / area.total * 100) : 0;
        return '<div class="dispo-area"><div class="dispo-line"><strong>' + ui.escapar(area.nombre) +
          "</strong><span>" + area.disponibles + " / " + area.total + " libres</span></div>" +
          '<div class="barra" role="img" aria-label="' + porcentaje + '% de camas disponibles en ' +
          ui.escapar(area.nombre) + '"><i style="width:' + porcentaje + '%"></i></div></div>';
      }).join("") : '<p class="dispo-vacio">Este centro todavía no tiene áreas.</p>';
      return '<article class="dispo-card"><header><h3>' + ui.escapar(centro.nombre) + "</h3><span>" +
        centro.disponibles + " de " + centro.total + " libres</span></header>" + areas + "</article>";
    }).join("");
  }

  function pintarHabitaciones() {
    var filas = datos.habitaciones.map(function (h) {
      return "<tr><td>" + ui.escapar(h.numero) + "</td><td>" + ui.escapar(h.piso) + "</td><td>" +
        ui.escapar(h.tipo) + "</td><td>" + ui.escapar(h.areaNombre) + "</td><td>" +
        ui.escapar(h.centroNombre) + '</td><td class="num">' + h.camasCount +
        '</td><td class="num">' + h.disponiblesCount + '</td><td class="num">' +
        '<button class="btn secundario chico" data-habitacion-editar="' + ui.escapar(h.id) +
        '">Editar</button> <button class="btn secundario chico" data-habitacion-eliminar="' +
        ui.escapar(h.id) + '">Eliminar</button></td></tr>';
    });
    ui.pintarTabla("tablaHabitaciones", filas, 8, "No hay habitaciones con esos filtros.");
    ui.contador("contadorHabitaciones", datos.habitaciones.length, "habitación", "habitaciones");
  }

  function pintarCamas() {
    var filas = datos.camas.map(function (c) {
      var acciones = "";
      if (c.estado === "Disponible" && !c.pacienteId) {
        acciones += '<button class="btn secundario chico" data-cama-asignar="' + ui.escapar(c.id) +
          '">Asignar</button> ';
      }
      if (c.pacienteId) {
        acciones += '<button class="btn secundario chico" data-cama-liberar="' + ui.escapar(c.id) +
          '">Liberar</button> ';
      }
      acciones += '<button class="btn secundario chico" data-cama-editar="' + ui.escapar(c.id) +
        '">Editar</button> <button class="btn secundario chico" data-cama-eliminar="' +
        ui.escapar(c.id) + '">Eliminar</button>';
      return "<tr><td>" + ui.escapar(c.codigo) + "</td><td>" + ui.escapar(c.habitacionNumero) +
        "</td><td>" + ui.escapar(c.areaNombre) + "</td><td>" + ui.escapar(c.centroNombre) +
        "</td><td>" + estadoCama(c.estado) + "</td><td>" +
        ui.escapar(c.pacienteNombre || "Sin asignar") + '</td><td class="num">' + acciones + "</td></tr>";
    });
    ui.pintarTabla("tablaCamas", filas, 7, "No hay camas con esos filtros.");
    ui.contador("contadorCamas", datos.camas.length, "cama", "camas");
    llenarAsignacion();
  }

  function llenarAsignacion() {
    var libres = datos.camas.filter(function (c) {
      return c.estado === "Disponible" && !c.pacienteId;
    });
    // `cama` solo trae camas realmente asignadas; los textos del Sprint 1 no bloquean.
    var sinCama = datos.pacientes.filter(function (p) { return !p.cama; });
    var cama = el("camaLibre").value, paciente = el("pacienteSinCama").value;
    llenar(el("camaLibre"), libres.map(function (c) {
      return {valor: c.id, texto: c.codigo + " · " + c.areaNombre + " · " + c.centroNombre};
    }), "Selecciona una cama", cama);
    llenar(el("pacienteSinCama"), sinCama.map(function (p) {
      return {valor: p.id, texto: p.nombres + " · " + p.cedula +
        (p.camaHeredada ? " · cama heredada: " + p.camaHeredada : "")};
    }), "Selecciona un paciente", paciente);
    var vacio = !libres.length || !sinCama.length;
    el("sinAsignacion").style.display = vacio ? "block" : "none";
    el("formAsignar").style.display = vacio ? "none" : "";
  }

  function filtrosCamas() {
    var filtros = {};
    ["filtroEstado"].forEach(function (id) {
      if (valor(id)) filtros.estado = valor(id);
    });
    if (valor("filtroCamas")) filtros.q = valor("filtroCamas");
    return filtros;
  }

  function filtrosZona() {
    var filtros = {};
    if (valor("filtroCentro")) filtros.centroId = valor("filtroCentro");
    if (valor("filtroArea")) filtros.areaId = valor("filtroArea");
    return filtros;
  }

  async function cargar() {
    var zona = filtrosZona();
    var camasFiltros = Object.assign({}, zona, filtrosCamas());
    var respuestas = await Promise.all([
      api.listar("habitaciones", zona),
      api.listar("camas", camasFiltros),
      api.listar("centros"),
      api.listar("areas"),
      api.listar("pacientes"),
      api.disponibilidad(zona),
      api.listar("habitaciones")
    ]);
    datos.habitaciones = respuestas[0];
    datos.camas = respuestas[1];
    datos.centros = respuestas[2];
    datos.areas = respuestas[3];
    datos.pacientes = respuestas[4];
    datos.disponibilidad = respuestas[5];
    datos.habitacionesTodas = respuestas[6];
    llenarSelectores();
    pintarDisponibilidad();
    pintarHabitaciones();
    pintarCamas();
  }

  function recargar(mensaje, tipo) {
    return cargar().then(function () {
      if (mensaje) ui.aviso(mensaje, tipo || "ok");
    });
  }

  function datosHabitacion() {
    return {areaId: valor("areaId"), numero: valor("numero"), piso: valor("piso"), tipo: valor("tipoHabitacion")};
  }

  function datosCama(actual) {
    return {
      habitacionId: valor("habitacionId"), codigo: valor("codigo"),
      estado: valor("estadoCama"), pacienteId: actual ? actual.pacienteId : "",
      observacion: valor("observacion")
    };
  }

  function habitacionPorId(id) {
    return datos.habitacionesTodas.filter(function (h) { return h.id === id; })[0] ||
      datos.habitaciones.filter(function (h) { return h.id === id; })[0];
  }

  function camaPorId(id) {
    return datos.camas.filter(function (c) { return c.id === id; })[0];
  }

  function limpiarFormularioHabitacion() {
    editandoHabitacion = null;
    el("formHabitacion").reset();
    el("formHabitacion").querySelector('[type="submit"]').textContent = "Guardar habitación";
  }

  function limpiarFormularioCama() {
    editandoCama = null;
    el("formCama").reset();
    el("formCama").querySelector('[type="submit"]').textContent = "Guardar cama";
  }

  H.ui.iniciar(async function () {
    var formHabitacion = el("formHabitacion");
    var formCama = el("formCama");
    var formAsignar = el("formAsignar");

    formHabitacion.addEventListener("reset", function () {
      editandoHabitacion = null;
      formHabitacion.querySelector('[type="submit"]').textContent = "Guardar habitación";
      ui.limpiarErrores(formHabitacion);
    });
    formCama.addEventListener("reset", function () {
      editandoCama = null;
      formCama.querySelector('[type="submit"]').textContent = "Guardar cama";
      ui.limpiarErrores(formCama);
    });

    formHabitacion.addEventListener("submit", function (evento) {
      evento.preventDefault();
      var id = editandoHabitacion;
      ui.limpiarErrores(formHabitacion);
      ui.ejecutar(formHabitacion, async function () {
        await api.guardar("habitaciones", datosHabitacion(), id);
        limpiarFormularioHabitacion();
        await recargar(id ? "Habitación actualizada." : "Habitación registrada.");
      });
    });

    formCama.addEventListener("submit", function (evento) {
      evento.preventDefault();
      var id = editandoCama;
      var actual = id ? camaPorId(id) : null;
      ui.limpiarErrores(formCama);
      ui.ejecutar(formCama, async function () {
        await api.guardar("camas", datosCama(actual), id);
        limpiarFormularioCama();
        await recargar(id ? "Cama actualizada." : "Cama registrada.");
      });
    });

    formAsignar.addEventListener("submit", function (evento) {
      evento.preventDefault();
      var cama = camaPorId(valor("camaLibre"));
      var pacienteId = valor("pacienteSinCama");
      ui.limpiarErrores(formAsignar);
      if (!cama) return ui.error("camaLibre", "Selecciona una cama disponible.");
      if (!pacienteId) return ui.error("pacienteSinCama", "Selecciona un paciente sin cama.");
      ui.ejecutar(formAsignar, async function () {
        await api.guardar("camas", {
          habitacionId: cama.habitacionId, codigo: cama.codigo, estado: "Ocupada",
          pacienteId: pacienteId, observacion: cama.observacion || ""
        }, cama.id);
        await recargar("Cama asignada. El paciente ya figura internado.", "ok");
      });
    });

    el("tablaHabitaciones").addEventListener("click", function (evento) {
      var boton = evento.target.closest("button");
      if (!boton) return;
      var editar = boton.getAttribute("data-habitacion-editar");
      var eliminar = boton.getAttribute("data-habitacion-eliminar");
      if (eliminar) {
        if (!confirm("¿Eliminar esta habitación? También se eliminarán sus camas.")) return;
        ui.ejecutar(boton, async function () {
          await api.eliminar("habitaciones", eliminar);
          if (editandoHabitacion === eliminar) limpiarFormularioHabitacion();
          await recargar("Habitación eliminada.", "info");
        });
      } else if (editar) {
        var habitacion = habitacionPorId(editar);
        if (!habitacion) return;
        el("areaId").value = habitacion.areaId;
        el("numero").value = habitacion.numero;
        el("piso").value = habitacion.piso;
        el("tipoHabitacion").value = habitacion.tipo;
        editandoHabitacion = editar;
        formHabitacion.querySelector('[type="submit"]').textContent = "Actualizar habitación";
        ui.limpiarErrores(formHabitacion);
        formHabitacion.scrollIntoView({behavior: "smooth", block: "center"});
      }
    });

    el("tablaCamas").addEventListener("click", function (evento) {
      var boton = evento.target.closest("button");
      if (!boton) return;
      var editar = boton.getAttribute("data-cama-editar");
      var eliminar = boton.getAttribute("data-cama-eliminar");
      var asignar = boton.getAttribute("data-cama-asignar");
      var liberar = boton.getAttribute("data-cama-liberar");
      var cama = camaPorId(editar || eliminar || asignar || liberar);
      if (!cama) return;
      if (eliminar) {
        if (!confirm("¿Eliminar la cama " + cama.codigo + "?")) return;
        ui.ejecutar(boton, async function () {
          await api.eliminar("camas", eliminar);
          if (editandoCama === eliminar) limpiarFormularioCama();
          await recargar("Cama eliminada.", "info");
        });
      } else if (liberar) {
        if (!confirm("¿Liberar la cama " + cama.codigo + " y desvincular al paciente?")) return;
        ui.ejecutar(boton, async function () {
          await api.guardar("camas", {
            habitacionId: cama.habitacionId, codigo: cama.codigo, estado: "Disponible",
            pacienteId: "", observacion: cama.observacion || ""
          }, cama.id);
          await recargar("Cama " + cama.codigo + " liberada.", "info");
        });
      } else if (asignar) {
        el("camaLibre").value = cama.id;
        formAsignar.scrollIntoView({behavior: "smooth", block: "center"});
        el("pacienteSinCama").focus();
      } else if (editar) {
        el("habitacionId").value = cama.habitacionId;
        el("codigo").value = cama.codigo;
        el("estadoCama").value = cama.estado;
        el("observacion").value = cama.observacion || "";
        editandoCama = editar;
        formCama.querySelector('[type="submit"]').textContent = "Actualizar cama";
        ui.limpiarErrores(formCama);
        formCama.scrollIntoView({behavior: "smooth", block: "center"});
      }
    });

    ["filtroCentro", "filtroArea", "filtroEstado"].forEach(function (id) {
      el(id).addEventListener("change", function () {
        if (id === "filtroCentro") {
          llenarSelectores();
          el("filtroArea").value = "";
        }
        cargar().catch(function (error) { ui.aviso(error.message, "error"); });
      });
    });
    var temporizador;
    el("filtroCamas").addEventListener("input", function () {
      clearTimeout(temporizador);
      temporizador = setTimeout(function () {
        cargar().catch(function (error) { ui.aviso(error.message, "error"); });
      }, 220);
    });

    await ui.ejecutar(formHabitacion, cargar, true);
  });
})(window.Hospital);
