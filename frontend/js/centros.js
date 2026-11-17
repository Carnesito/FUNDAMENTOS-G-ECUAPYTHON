/* Centros: el servidor devuelve también el número de áreas relacionadas. */
(function (H) {
  "use strict";
  var ui = H.ui;
  H.crud({
    coleccion: "centros", formulario: "formCentro", tabla: "tablaCentros", columnas: 5,
    contador: "contadorCentros", singular: "centro", plural: "centros",
    campos: ["nombre", "direccion", "telefono"],
    celdas: function (c) {
      return "<td>" + ui.escapar(c.nombre) + "</td><td>" + ui.escapar(c.direccion) + "</td><td>" +
        ui.escapar(c.telefono) + '</td><td class="num">' + c.areasCount + "</td>";
    }
  });
})(window.Hospital);
