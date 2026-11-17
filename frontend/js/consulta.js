/* La búsqueda y las fichas se consultan directamente en el backend. */
(function (H) {
  "use strict";
  var ui = H.ui, api = H.api;
  function ficha(p) {
    return '<article class="ficha"><header><div><h3>' + ui.escapar(p.nombres) + '</h3><div class="cedula">Cédula ' +
      ui.escapar(p.cedula) + '</div></div>' + ui.triaje(p.triaje) + '</header><dl>' +
      '<div><dt>Fecha de nacimiento</dt><dd>' + ui.fecha(p.nacimiento) + '</dd></div>' +
      '<div><dt>Edad</dt><dd>' + ui.edad(p.nacimiento) + '</dd></div>' +
      '<div><dt>Teléfono</dt><dd>' + ui.escapar(p.telefono) + '</dd></div>' +
      '<div><dt>Triaje</dt><dd>' + ui.escapar(p.triaje || "Sin asignar") + '</dd></div>' +
      '<div><dt>Cama</dt><dd>' + ui.escapar(p.cama || "Sin asignar") + '</dd></div></dl></article>';
  }
  H.ui.iniciar(async function () {
    var formulario = document.getElementById("formConsulta");
    var resultado = document.getElementById("resultado");
    formulario.addEventListener("submit", function (evento) {
      evento.preventDefault();
      var criterio = document.getElementById("criterio").value.trim();
      var tipo = document.getElementById("tipo").value;
      if (!criterio) return ui.error("criterio", "Escribe una cédula o unos apellidos.");
      if (tipo === "cedula" && !ui.cedulaValida(criterio)) return ui.error("criterio", "La cédula debe tener 10 dígitos.");
      ui.error("criterio", "");
      ui.ejecutar(formulario, async function () {
        var filtros = {}; filtros[tipo] = criterio;
        var pacientes = await api.listar("pacientes", filtros);
        resultado.innerHTML = pacientes.length ? pacientes.map(ficha).join("") :
          '<div class="vacio-estado">Paciente no registrado. Verifica el dato o regístralo en <a href="pacientes.html">Pacientes</a>.</div>';
        ui.aviso(pacientes.length ? "Pacientes encontrados: " + pacientes.length : "Paciente no registrado.", pacientes.length ? "ok" : "error");
      });
    });
    document.getElementById("criterio").addEventListener("input", function () {
      if (!this.value.trim()) resultado.innerHTML = "";
    });
    document.getElementById("tablaConsulta").addEventListener("click", function (evento) {
      var boton = evento.target.closest("[data-ver]");
      if (!boton) return;
      ui.ejecutar(boton, async function () {
        resultado.innerHTML = ficha(await api.obtener("pacientes", boton.getAttribute("data-ver")));
        resultado.scrollIntoView({behavior: "smooth", block: "center"});
      });
    });
    await ui.ejecutar(formulario, async function () {
      var pacientes = await api.listar("pacientes");
      ui.pintarTabla("tablaConsulta", pacientes.map(function (p) {
        return "<tr><td>" + ui.escapar(p.cedula) + "</td><td>" + ui.escapar(p.nombres) + "</td><td>" +
          ui.triaje(p.triaje) + "</td><td>" + ui.escapar(p.cama || "Sin asignar") +
          '</td><td class="num"><button class="btn secundario chico" data-ver="' + ui.escapar(p.id) + '">Ver ficha</button></td></tr>';
      }), 5, "No hay pacientes registrados.");
      ui.contador("contadorPacientes", pacientes.length, "paciente", "pacientes");
    }, true);
  });
})(window.Hospital);
