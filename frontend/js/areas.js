/* Áreas: los centros y las áreas se consultan mediante recursos REST separados. */
(function (H) {
  "use strict";
  var ui = H.ui;
  H.crud({
    coleccion: "areas", formulario: "formArea", tabla: "tablaAreas", columnas: 4,
    contador: "contadorAreas", singular: "área", plural: "áreas", campos: ["centroId", "nombre", "tipo"],
    preparar: async function () {
      var centros = await H.api.listar("centros");
      ["centroId", "filtro"].forEach(function (id) {
        var select = document.getElementById(id), valor = select.value;
        var etiqueta = id === "centroId" ? "Selecciona un centro" : "Todos los centros";
        select.innerHTML = '<option value="">' + etiqueta + "</option>" + centros.map(function (c) {
          return '<option value="' + ui.escapar(c.id) + '">' + ui.escapar(c.nombre) + "</option>";
        }).join("");
        select.value = centros.some(function (c) { return c.id === valor; }) ? valor : "";
      });
      document.getElementById("sinCentros").style.display = centros.length ? "none" : "block";
      document.getElementById("formArea").style.display = centros.length ? "" : "none";
    },
    filtros: function () { return {centroId: document.getElementById("filtro").value}; },
    celdas: function (a) {
      return "<td>" + ui.escapar(a.nombre) + "</td><td>" + ui.escapar(a.tipo) + "</td><td>" +
        ui.escapar(a.centroNombre) + "</td>";
    }
  });
})(window.Hospital);
