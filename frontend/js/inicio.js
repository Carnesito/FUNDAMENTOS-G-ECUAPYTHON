/* Los indicadores se calculan en SQLite, no en una copia de los registros. */
Hospital.ui.iniciar(async function () {
  var resumen = await Hospital.api.resumen();
  document.getElementById("statPacientes").textContent = resumen.pacientes;
  document.getElementById("statCentros").textContent = resumen.centros;
  document.getElementById("statAreas").textContent = resumen.areas;
  document.getElementById("statCamas").textContent = resumen.camasDisponibles;
});
