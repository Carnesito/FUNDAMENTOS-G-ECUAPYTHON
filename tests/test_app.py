"""Pruebas de integración contra una base SQLite temporal, sin tocar los datos reales."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from backend import create_app


class HospitalTest(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.db = Path(self.temporal.name) / "hospital.db"
        self.app = create_app(self.db)
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()

    def paciente(self, **cambios):
        datos = dict(cedula="1234567890", nombres="Paciente de prueba",
                     nacimiento="1995-05-10", telefono="0991234567", triaje="Nivel II", cama="A-01")
        datos.update(cambios)
        return datos

    def test_paginas_recursos_y_archivos_privados(self):
        for ruta in ["/", "/index.html", "/pacientes.html", "/consulta.html",
                     "/centros.html", "/areas.html", "/css/style.css", "/js/api.js", "/js/crud.js", "/assets/hospital.svg"]:
            with self.subTest(ruta=ruta), self.cliente.get(ruta) as respuesta:
                self.assertEqual(respuesta.status_code, 200)
        for ruta in ["/data/hospital.db", "/app.py", "/requirements.txt", "/css/../app.py", "/noexiste.html"]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.cliente.get(ruta).status_code, 404)

    def test_registro_persiste_al_recrear_aplicacion(self):
        respuesta = self.cliente.post("/api/pacientes", json=self.paciente())
        self.assertEqual(respuesta.status_code, 201)
        identificador = respuesta.json["registro"]["id"]
        nuevo_cliente = create_app(self.db).test_client()
        registros = nuevo_cliente.get("/api/datos").json["pacientes"]
        self.assertEqual(len(registros), 4)
        self.assertEqual(registros[-1]["id"], identificador)
        with closing(sqlite3.connect(self.db)) as conexion:
            self.assertEqual(conexion.execute("SELECT cedula FROM pacientes WHERE id = ?", (identificador,)).fetchone()[0], "1234567890")

    def test_paciente_duplicado_y_validaciones(self):
        self.cliente.post("/api/pacientes", json=self.paciente())
        repetido = self.cliente.post("/api/pacientes", json=self.paciente())
        self.assertEqual(repetido.status_code, 409)
        self.assertEqual(repetido.json["campo"], "cedula")
        for cambios, campo in [({"cedula": "123"}, "cedula"),
                               ({"nacimiento": "2999-01-01"}, "nacimiento"),
                               ({"nacimiento": "2020-02-31"}, "nacimiento"),
                               ({"telefono": "abc"}, "telefono"),
                               ({"nombres": ""}, "nombres"),
                               ({"triaje": "Inventado"}, "triaje"),
                               ({"cedula": 1234567890}, "cedula")]:
            with self.subTest(cambios=cambios):
                resultado = self.cliente.post("/api/pacientes", json=self.paciente(**cambios))
                self.assertEqual(resultado.status_code, 400)
                self.assertEqual(resultado.json["campo"], campo)

    def test_centros_unicos_areas_por_sede_y_borrado_atomico(self):
        centro = dict(nombre="Clínica Nueva", direccion="Calle Uno", telefono="022345678")
        resultado = self.cliente.post("/api/centros", json=centro)
        self.assertEqual(resultado.status_code, 201)
        identificador = resultado.json["registro"]["id"]
        duplicado = self.cliente.post("/api/centros", json={**centro, "nombre": " CLINICA NUEVA "})
        self.assertEqual(duplicado.status_code, 409)
        area = dict(centroId=identificador, nombre="Observación", tipo="Emergencia")
        self.assertEqual(self.cliente.post("/api/areas", json=area).status_code, 201)
        self.assertEqual(self.cliente.post("/api/areas", json={**area, "nombre": "OBSERVACION"}).status_code, 409)
        self.assertEqual(self.cliente.post("/api/areas", json={**area, "centroId": "c1"}).status_code, 201)
        self.assertEqual(self.cliente.post("/api/areas", json={**area, "centroId": "inexistente"}).status_code, 400)
        borrado = self.cliente.delete("/api/centros/" + identificador)
        self.assertEqual(borrado.status_code, 204)
        areas = self.cliente.get("/api/areas").json["registros"]
        self.assertFalse(any(a["centroId"] == identificador for a in areas))
        self.assertTrue(any(a["nombre"] == "Observación" for a in areas))

    def test_datos_vacios_no_se_reponen_al_reiniciar(self):
        datos = self.cliente.get("/api/datos").json
        for paciente in datos["pacientes"]:
            self.cliente.delete("/api/pacientes/" + paciente["id"])
        for centro in datos["centros"]:
            self.cliente.delete("/api/centros/" + centro["id"])
        nuevo_cliente = create_app(self.db).test_client()
        self.assertEqual(nuevo_cliente.get("/api/datos").json, {"pacientes": [], "centros": [], "areas": []})

    def test_errores_json_origen_y_host(self):
        self.assertEqual(self.cliente.post("/api/pacientes", json=[]).status_code, 400)
        self.assertEqual(self.cliente.post("/api/pacientes", data="no json").status_code, 415)
        self.assertEqual(self.cliente.post("/api/pacientes", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.cliente.post("/api/pacientes", json=self.paciente(), headers={"Origin": "https://otro.test"}).status_code, 403)
        self.assertEqual(self.cliente.post("/api/desconocida", json={}).status_code, 404)
        self.assertEqual(self.cliente.delete("/api/pacientes/noexiste").status_code, 404)
        self.assertEqual(self.cliente.get("/api/datos", headers={"Host": "otro.test"}).status_code, 400)
        self.assertEqual(self.cliente.get("/api/datos").headers["Cache-Control"], "no-store")

    def test_envios_concurrentes_no_duplican_cedula(self):
        def registrar(_):
            with self.app.test_client() as cliente:
                return cliente.post("/api/pacientes", json=self.paciente()).status_code
        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = list(hilos.map(registrar, range(2)))
        self.assertEqual(sorted(resultados), [201, 409])

    def test_crud_completo_por_recurso(self):
        ejemplos = {
            "pacientes": (self.paciente(), "nombres", "Paciente actualizado"),
            "centros": (dict(nombre="Centro Uno", direccion="Calle Primera", telefono="0991234567"), "direccion", "Calle Segunda"),
            "areas": (dict(centroId="c1", nombre="Área de pruebas", tipo="Laboratorio"), "nombre", "Área actualizada"),
        }
        for coleccion, (entrada, campo, valor) in ejemplos.items():
            with self.subTest(coleccion=coleccion):
                creada = self.cliente.post("/api/" + coleccion, json=entrada)
                self.assertEqual(creada.status_code, 201)
                ruta = creada.headers["Location"]
                self.assertNotIn("datos", creada.json)
                self.assertNotIn("nombre_clave", creada.json["registro"])
                self.assertEqual(self.cliente.get(ruta).json["registro"][campo], entrada[campo])
                modificada = self.cliente.put(ruta, json={**entrada, campo: valor})
                self.assertEqual(modificada.status_code, 200)
                self.assertEqual(self.cliente.get(ruta).json["registro"][campo], valor)
                persistida = create_app(self.db).test_client().get(ruta)
                self.assertEqual(persistida.json["registro"][campo], valor)
                self.assertEqual(self.cliente.delete(ruta).status_code, 204)
                self.assertEqual(self.cliente.get(ruta).status_code, 404)

    def test_busquedas_sql_y_relaciones(self):
        for filtros in [{"cedula": "0951234567"}, {"apellidos": "vEra LOPEZ"}, {"q": "FERNANDA"}]:
            with self.subTest(filtros=filtros):
                respuesta = self.cliente.get("/api/pacientes", query_string=filtros)
                self.assertEqual(respuesta.json["total"], 1)
                self.assertEqual(respuesta.json["registros"][0]["id"], "p1")
        self.assertEqual(self.cliente.get("/api/pacientes?q=%25").json["total"], 0)
        self.assertEqual(self.cliente.get("/api/pacientes?q=%27%20OR%201%3D1").json["total"], 0)
        areas = self.cliente.get("/api/areas?centroId=c1").json["registros"]
        self.assertEqual(len(areas), 2)
        self.assertTrue(all(a["centroNombre"] == "Hospital Santa Vida" for a in areas))
        centro = self.cliente.get("/api/centros/c1").json["registro"]
        self.assertEqual(centro["areasCount"], 2)
        self.assertEqual(self.cliente.get("/api/resumen").json, {"pacientes": 3, "centros": 2, "areas": 3})

    def test_actualizaciones_invalidas_no_modifican_la_base(self):
        ruta = "/api/pacientes/p1"
        anterior = self.cliente.get(ruta).json["registro"]
        self.assertEqual(self.cliente.put(ruta, json={**anterior, "cedula": "0104567890"}).status_code, 409)
        self.assertEqual(self.cliente.put(ruta, json={**anterior, "telefono": "incorrecto"}).status_code, 400)
        self.assertEqual(self.cliente.get(ruta).json["registro"], anterior)
        self.assertEqual(self.cliente.put(ruta, json=anterior, headers={"Origin": "https://otro.test"}).status_code, 403)
        self.assertEqual(self.cliente.put("/api/pacientes/noexiste", json=self.paciente()).status_code, 404)

    def test_backend_puede_funcionar_sin_frontend(self):
        cliente_api = create_app(self.db, servir_frontend=False).test_client()
        self.assertEqual(cliente_api.get("/").status_code, 404)
        self.assertEqual(cliente_api.get("/js/api.js").status_code, 404)
        self.assertEqual(cliente_api.get("/api/salud").json["estado"], "ok")
        self.assertEqual(cliente_api.get("/api/pacientes").status_code, 200)


if __name__ == "__main__":
    unittest.main()
