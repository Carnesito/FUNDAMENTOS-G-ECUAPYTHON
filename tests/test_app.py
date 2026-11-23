"""Pruebas de integración contra una base SQLite temporal, sin tocar los datos reales."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from backend import create_app
from backend.database import _reconciliar_camas_heredadas


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
                     nacimiento="1995-05-10", telefono="0991234567", triaje="Nivel II",
                     motivo="Control de signos vitales", signos="TA 120/80 · FC 80",
                     triaje_fecha="2026-11-21 09:30")
        datos.update(cambios)
        return datos

    def test_paginas_recursos_y_archivos_privados(self):
        for ruta in ["/", "/index.html", "/pacientes.html", "/consulta.html",
                     "/centros.html", "/areas.html", "/camas.html", "/css/style.css", "/js/api.js",
                     "/js/crud.js", "/js/camas.js", "/assets/hospital.svg"]:
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
        self.assertTrue(any(registro["id"] == identificador for registro in registros))
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
        self.assertEqual(nuevo_cliente.get("/api/datos").json,
                         {"pacientes": [], "centros": [], "areas": [], "habitaciones": [], "camas": []})

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
        self.assertEqual(self.cliente.get("/api/resumen").json,
                         {"pacientes": 3, "centros": 2, "areas": 4, "habitaciones": 2, "camas": 4,
                          "camasDisponibles": 3, "camasOcupadas": 1, "camasMantenimiento": 0})

    def test_actualizaciones_invalidas_no_modifican_la_base(self):
        ruta = "/api/pacientes/p1"
        anterior = self.cliente.get(ruta).json["registro"]
        self.assertEqual(self.cliente.put(ruta, json={**anterior, "cedula": "0104567890"}).status_code, 409)
        self.assertEqual(self.cliente.put(ruta, json={**anterior, "telefono": "incorrecto"}).status_code, 400)
        self.assertEqual(self.cliente.get(ruta).json["registro"], anterior)
        self.assertEqual(self.cliente.put(ruta, json=anterior, headers={"Origin": "https://otro.test"}).status_code, 403)
        self.assertEqual(self.cliente.put("/api/pacientes/noexiste", json=self.paciente()).status_code, 404)

    def test_triaje_ordena_por_gravedad_y_valida_fecha(self):
        urgente = self.cliente.post("/api/pacientes", json=self.paciente(
            cedula="1111111111", nombres="AAA Urgente", triaje="Nivel I",
            motivo="Dolor torácico", signos="TA 90/60 · FC 120",
            triaje_fecha="2026-11-23T10:00"))
        self.assertEqual(urgente.status_code, 201)
        lista = self.cliente.get("/api/pacientes").json["registros"]
        self.assertEqual(lista[0]["id"], urgente.json["registro"]["id"])
        self.assertEqual(lista[-1]["id"], "p3")
        self.assertEqual(self.cliente.get("/api/pacientes?triaje=Nivel I").json["total"], 1)
        invalida = self.cliente.post("/api/pacientes", json=self.paciente(
            cedula="2222222222", triaje_fecha="ayer por la tarde"))
        self.assertEqual(invalida.status_code, 400)
        self.assertEqual(invalida.json["campo"], "triaje_fecha")
        self.assertEqual(self.cliente.post("/api/pacientes", json=self.paciente(
            cedula="3333333333", motivo="x" * 201)).status_code, 400)

    def test_habitaciones_camas_disponibilidad_y_asignacion(self):
        habitacion = self.cliente.post("/api/habitaciones", json={
            "areaId": "a1", "numero": "N-01", "piso": "3", "tipo": "Doble"})
        self.assertEqual(habitacion.status_code, 201)
        habitacion_id = habitacion.json["registro"]["id"]
        repetida = self.cliente.post("/api/habitaciones", json={
            "areaId": "a1", "numero": "n-01", "piso": "3", "tipo": "Doble"})
        self.assertEqual(repetida.status_code, 409)
        self.assertEqual(self.cliente.post("/api/habitaciones", json={
            "areaId": "a1", "numero": "N-02", "piso": "3", "tipo": "Inventado"}).status_code, 400)

        cama = self.cliente.post("/api/camas", json={
            "habitacionId": habitacion_id, "codigo": "N-01-A", "estado": "Disponible",
            "pacienteId": "", "observacion": ""})
        self.assertEqual(cama.status_code, 201)
        cama_id = cama.json["registro"]["id"]
        self.assertEqual(cama.json["registro"]["estado"], "Disponible")
        self.assertEqual(self.cliente.post("/api/camas", json={
            "habitacionId": habitacion_id, "codigo": "n-01-a", "estado": "Disponible",
            "pacienteId": "", "observacion": ""}).status_code, 409)

        paciente = self.cliente.post("/api/pacientes", json=self.paciente()).json["registro"]
        ruta = "/api/camas/" + cama_id
        asignada = self.cliente.put(ruta, json={
            "habitacionId": habitacion_id, "codigo": "N-01-A", "estado": "Disponible",
            "pacienteId": paciente["id"], "observacion": ""})
        self.assertEqual(asignada.status_code, 200)
        self.assertEqual(asignada.json["registro"]["estado"], "Ocupada")
        self.assertEqual(self.cliente.get("/api/pacientes/" + paciente["id"]).json["registro"]["cama"],
                         "N-01-A")
        self.assertEqual(self.cliente.get("/api/camas?estado=Disponible").json["total"], 3)
        self.assertEqual(self.cliente.get("/api/disponibilidad").json["totales"]["ocupadas"], 2)

        otra = self.cliente.post("/api/camas", json={
            "habitacionId": habitacion_id, "codigo": "N-01-B", "estado": "Disponible",
            "pacienteId": "", "observacion": ""}).json["registro"]
        duplicada = self.cliente.put("/api/camas/" + otra["id"], json={
            "habitacionId": habitacion_id, "codigo": "N-01-B", "estado": "Disponible",
            "pacienteId": paciente["id"], "observacion": ""})
        self.assertEqual(duplicada.status_code, 400)
        self.assertEqual(duplicada.json["campo"], "pacienteId")

        liberada = self.cliente.put(ruta, json={
            "habitacionId": habitacion_id, "codigo": "N-01-A", "estado": "Ocupada",
            "pacienteId": "", "observacion": ""})
        self.assertEqual(liberada.json["registro"]["estado"], "Disponible")
        self.assertEqual(self.cliente.get("/api/pacientes/" + paciente["id"]).json["registro"]["cama"], "")
        self.assertEqual(self.cliente.delete("/api/habitaciones/" + habitacion_id).status_code, 204)
        self.assertEqual(self.cliente.get("/api/camas/" + cama_id).status_code, 404)

    def test_reconciliacion_de_camas_heredadas(self):
        with closing(sqlite3.connect(":memory:")) as conexion:
            conexion.executescript("""
                CREATE TABLE pacientes (id TEXT PRIMARY KEY, nombres TEXT,
                    cama TEXT NOT NULL DEFAULT '', cama_heredada TEXT NOT NULL DEFAULT '');
                CREATE TABLE camas (id TEXT PRIMARY KEY, codigo TEXT, codigo_clave TEXT,
                    pacienteId TEXT NOT NULL DEFAULT '', estado TEXT);
                INSERT INTO pacientes (id, nombres, cama) VALUES
                    ('a', 'Ana', 'UCI-02'), ('b', 'Beto', '1'), ('c', 'Carla', '');
                INSERT INTO camas VALUES ('ca', 'UCI-02', 'uci-02', '', 'Disponible');
            """)
            _reconciliar_camas_heredadas(conexion)
            self.assertEqual(conexion.execute(
                "SELECT cama, cama_heredada FROM pacientes WHERE id = 'a'").fetchone(), ("UCI-02", ""))
            self.assertEqual(conexion.execute(
                "SELECT pacienteId, estado FROM camas WHERE id = 'ca'").fetchone(), ("a", "Ocupada"))
            self.assertEqual(conexion.execute(
                "SELECT cama, cama_heredada FROM pacientes WHERE id = 'b'").fetchone(), ("", "1"))

    def test_base_del_sprint1_migra_y_el_paciente_puede_recibir_cama(self):
        ruta = Path(self.temporal.name) / "sprint1.db"
        with closing(sqlite3.connect(ruta)) as conexion:
            conexion.executescript("""
                CREATE TABLE pacientes (
                    id TEXT PRIMARY KEY, cedula TEXT NOT NULL UNIQUE, nombres TEXT NOT NULL,
                    nacimiento TEXT NOT NULL, telefono TEXT NOT NULL,
                    triaje TEXT NOT NULL DEFAULT '', cama TEXT NOT NULL DEFAULT '');
                INSERT INTO pacientes VALUES ('viejo', '1711111111', 'Paciente Heredado',
                    '1980-01-01', '0999999999', 'Nivel II', 'UCI-02');
                PRAGMA user_version = 1;
            """)
            conexion.commit()
        cliente = create_app(ruta).test_client()
        heredado = cliente.get("/api/pacientes/viejo").json["registro"]
        self.assertEqual(heredado["cama"], "")
        self.assertEqual(heredado["camaHeredada"], "UCI-02")
        self.assertIn(heredado["id"], [p["id"] for p in cliente.get("/api/pacientes").json["registros"]])

        centro = cliente.post("/api/centros", json={
            "nombre": "Centro Migrado", "direccion": "Calle Uno", "telefono": "022345678"}).json["registro"]
        area = cliente.post("/api/areas", json={
            "centroId": centro["id"], "nombre": "Hospitalización", "tipo": "Hospitalización"}).json["registro"]
        habitacion = cliente.post("/api/habitaciones", json={
            "areaId": area["id"], "numero": "101", "piso": "1", "tipo": "Individual"}).json["registro"]
        cama = cliente.post("/api/camas", json={
            "habitacionId": habitacion["id"], "codigo": "H-01", "estado": "Disponible",
            "pacienteId": "", "observacion": ""}).json["registro"]
        cliente.put("/api/camas/" + cama["id"], json={
            "habitacionId": habitacion["id"], "codigo": "H-01", "estado": "Disponible",
            "pacienteId": "viejo", "observacion": ""})
        asignado = cliente.get("/api/pacientes/viejo").json["registro"]
        self.assertEqual(asignado["cama"], "H-01")
        self.assertEqual(asignado["camaHeredada"], "")

    def test_backend_puede_funcionar_sin_frontend(self):
        cliente_api = create_app(self.db, servir_frontend=False).test_client()
        self.assertEqual(cliente_api.get("/").status_code, 404)
        self.assertEqual(cliente_api.get("/js/api.js").status_code, 404)
        self.assertEqual(cliente_api.get("/api/salud").json["estado"], "ok")
        self.assertEqual(cliente_api.get("/api/pacientes").status_code, 200)


if __name__ == "__main__":
    unittest.main()
