/* Pacientes: presentación y peticiones al backend. */
(function (H) {
  "use strict";
  var ui = H.ui;
  H.crud({
    coleccion: "pacientes", formulario: "formPaciente", tabla: "tablaPacientes", columnas: 7,
    contador: "contadorPacientes", singular: "paciente", plural: "pacientes",
    campos: ["cedula", "nombres", "nacimiento", "telefono", "triaje", "cama"],
    filtros: function () { return {q: document.getElementById("filtro").value.trim()}; },
    celdas: function (p) {
      return "<td>" + ui.escapar(p.cedula) + "</td><td>" + ui.escapar(p.nombres) + "</td><td>" +
        ui.edad(p.nacimiento) + "</td><td>" + ui.escapar(p.telefono) + "</td><td>" + ui.triaje(p.triaje) +
        "</td><td>" + ui.escapar(p.cama || "Sin asignar") + "</td>";
    }
  });
})(window.Hospital);
