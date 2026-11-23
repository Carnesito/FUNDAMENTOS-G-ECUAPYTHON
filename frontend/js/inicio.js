/* Los indicadores se calculan en SQLite, no en una copia de los registros. */
Hospital.ui.iniciar(async function () {
  var ui = Hospital.ui, api = Hospital.api;
  var resumen = await api.resumen();
  document.getElementById("statPacientes").textContent = resumen.pacientes;
  document.getElementById("statCentros").textContent = resumen.centros;
  document.getElementById("statAreas").textContent = resumen.areas;
  document.getElementById("statCamas").textContent = resumen.camasDisponibles;

  var respuestas = await Promise.all([api.disponibilidad(), api.listar("pacientes")]);
  pintarOcupacion(resumen, respuestas[0]);
  pintarTriaje(respuestas[1]);
  pintarPrioridad(respuestas[1]);
  document.getElementById("opsActualizado").textContent =
    "Actualizado a las " + new Date().toLocaleTimeString("es-EC", {hour: "2-digit", minute: "2-digit"});
});

function pintarOcupacion(resumen, disponibilidad) {
  var total = resumen.camas;
  var ocupadas = resumen.camasOcupadas;
  var libres = resumen.camasDisponibles;
  var mantenimiento = resumen.camasMantenimiento;
  var porcentaje = total ? Math.round(ocupadas / total * 100) : 0;
  document.getElementById("opsOcupadas").textContent = ocupadas;
  document.getElementById("opsTotal").textContent = total;
  document.getElementById("opsOcupacionPct").textContent = porcentaje + "% ocupado";
  document.getElementById("opsBarra").style.width = porcentaje + "%";
  document.getElementById("opsBarraImg").setAttribute("aria-label",
    porcentaje + "% de las camas están ocupadas (" + ocupadas + " de " + total + ")");
  document.getElementById("opsLibres").textContent = libres;
  document.getElementById("opsOcupadasLeyenda").textContent = ocupadas;
  document.getElementById("opsMantenimiento").textContent = mantenimiento;
  var centros = (disponibilidad.centros || []).length;
  var areas = (disponibilidad.totales || {}).areas || 0;
  document.getElementById("opsBarraImg").title = centros + " centros y " + areas + " áreas monitoreadas";
}

function pintarTriaje(pacientes) {
  var niveles = ["Nivel I", "Nivel II", "Nivel III", "Nivel IV", ""];
  var etiquetas = {"Nivel I": "Nivel I · Resucitación", "Nivel II": "Nivel II · Emergencia",
                   "Nivel III": "Nivel III · Urgencia", "Nivel IV": "Nivel IV · Menor",
                   "": "Sin clasificar"};
  var clases = {"Nivel I": "n1", "Nivel II": "n2", "Nivel III": "n3", "Nivel IV": "n4", "": "sin"};
  var conteo = {};
  niveles.forEach(function (nivel) { conteo[nivel] = 0; });
  pacientes.forEach(function (p) { conteo[p.triaje in conteo ? p.triaje : ""] += 1; });
  var maximo = Math.max.apply(null, niveles.map(function (nivel) { return conteo[nivel]; }).concat([1]));
  document.getElementById("opsTriajeTotal").textContent = pacientes.length +
    (pacientes.length === 1 ? " paciente" : " pacientes");
  var contenedor = document.getElementById("opsTriaje");
  contenedor.classList.remove("skeleton");
  contenedor.innerHTML = niveles.map(function (nivel) {
    var total = conteo[nivel];
    var ancho = Math.round(total / maximo * 100);
    return '<div class="triaje-fila"><div class="triaje-texto"><span class="tag ' +
      clases[nivel] + '">' + Hospital.ui.escapar(etiquetas[nivel]) +
      "</span><b>" + total + "</b></div><div class=\"barra barra-" +
      clases[nivel] + '"><i style="width:' + ancho + '%"></i></div></div>';
  }).join("");
}

function pintarPrioridad(pacientes) {
  var ui = Hospital.ui;
  var filas = pacientes.slice(0, 5).map(function (p) {
    var cama = p.cama ? ui.escapar(p.cama) :
      (p.camaHeredada ? '<span class="tag cama-heredada">Heredada: ' + ui.escapar(p.camaHeredada) + "</span>" :
        '<span class="sin-cama">Sin asignar</span>');
    return "<tr><td>" + ui.escapar(p.nombres) + '<span class="celda-nota">' + ui.escapar(p.cedula) +
      "</span></td><td>" + ui.triaje(p.triaje) + '</td><td class="motivo-celda">' +
      ui.escapar(p.motivo || "Sin motivo registrado") + "</td><td>" + cama + "</td></tr>";
  });
  ui.pintarTabla("tablaPrioridad", filas, 4, "Todavía no hay pacientes registrados.");
}
