/* Pacientes: registro con triaje y presentación de la lista por gravedad. */
(function (H) {
  "use strict";
  var ui = H.ui;
  H.crud({
    coleccion: "pacientes", formulario: "formPaciente", tabla: "tablaPacientes", columnas: 8,
    contador: "contadorPacientes", singular: "paciente", plural: "pacientes",
    campos: ["cedula", "nombres", "nacimiento", "telefono", "triaje", "motivo", "signos", "triaje_fecha"],
    filtros: function () { return {q: document.getElementById("filtro").value.trim()}; },
    celdas: function (p) {
      return "<td>" + ui.escapar(p.cedula) + "</td><td>" + ui.escapar(p.nombres) + "</td><td>" +
        ui.edad(p.nacimiento) + "</td><td>" + ui.escapar(p.telefono) + "</td><td>" + ui.triaje(p.triaje) +
        '</td><td class="motivo-celda" title="' + ui.escapar(p.motivo || "") + '">' +
        ui.escapar(p.motivo || "—") + "</td><td>" + ui.escapar(p.cama || "Sin asignar") + "</td>";
    }
  });

  H.ui.iniciar(function () {
    var campo = document.getElementById("triaje_fecha");
    function ahora() {
      var fecha = new Date();
      var dos = function (numero) { return String(numero).padStart(2, "0"); };
      campo.value = fecha.getFullYear() + "-" + dos(fecha.getMonth() + 1) + "-" + dos(fecha.getDate()) +
        "T" + dos(fecha.getHours()) + ":" + dos(fecha.getMinutes());
    }
    if (!campo.value) ahora();
    document.getElementById("formPaciente").addEventListener("reset", function () {
      setTimeout(ahora, 0);
    });
  });
})(window.Hospital);
