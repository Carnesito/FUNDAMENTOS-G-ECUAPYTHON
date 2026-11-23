# Sistema de Gestión Hospitalaria — Flask + SQLite

Aplicación de los Sprint 1 y 2 (pacientes, triaje, consulta, centros, áreas, habitaciones y camas)
con frontend y backend separados. Permite crear, consultar, editar y eliminar registros, clasificar
por gravedad y asignar camas disponibles. Los datos existentes de SQLite se conservan.

## Arquitectura

```text
Navegador: frontend HTML / CSS / JavaScript
        │  HTTP: GET, POST, PUT, DELETE /api/...
        ▼
Backend Flask: rutas → servicios → validaciones / repositorios
        │  SQL parametrizado y transacciones
        ▼
SQLite: data/hospital.db
```

- `frontend/` contiene las páginas, estilos, ilustraciones y controladores de interfaz.
  `js/api.js` hace peticiones HTTP; `js/crud.js` conecta los formularios y las tablas y
  `js/camas.js` controla la disponibilidad y la asignación. No utiliza localStorage ni datos
  simulados: las listas, fichas, filtros y contadores se consultan en el servidor.
- `backend/` implementa una API REST independiente. Valida también las solicitudes que llegan sin navegador.
  `repositorios.py` contiene SQL; `servicios.py` controla las transacciones; `rutas.py` expone JSON.
- SQLite aplica la cédula única, nombres normalizados únicos, códigos de cama únicos y relaciones
  entre centros, áreas, habitaciones y camas. Una cama solo puede pertenecer a un paciente y, al
  ocuparla, el paciente recibe el código en su ficha. Eliminar un centro elimina sus áreas,
  habitaciones y camas en la misma transacción y libera las referencias de los pacientes.
- En el uso normal, un servidor Waitress entrega el frontend y la API en la misma dirección.
  Para desarrollo también se pueden ejecutar en dos servidores independientes.

## Inicio automático y versión portable

**Windows de 64 bits, sin instalar Python:**

1. Extrae TODO `Hospital_Portable.zip`.
2. Haz doble clic en `Hospital_Portable/Hospital.exe`.
3. Se abrirá el navegador. Mantén abierta la ventana del programa mientras lo utilizas.
4. Para apagarlo, presiona Ctrl+C en esa ventana o ciérrala.

El ejecutable extraído también está en `dist/Hospital_Portable/Hospital.exe`.
No necesita internet. No lo ejecutes directamente dentro del ZIP.

**Código fuente:** abre `INICIAR.cmd` con doble clic. Necesita Python 3.10 o posterior
(y conexión solo la primera vez, para instalar dependencias). El script prepara `.venv`
y abre el programa automáticamente. No hace falta activar el entorno virtual.

La dirección habitual es http://127.0.0.1:5000. Si ese puerto está ocupado se elige
uno libre y se muestra la dirección correcta. Cerrar el navegador no apaga el servidor.
El programa escucha únicamente en este equipo.

## Comandos exactos en tu equipo

```powershell
cd "C:\Users\Jaag2\OneDrive\Documentos\Proyectos\FUNDAMENTOS SPRINTS\Entregable_Sprint_1\05_Aplicacion_Web"
.\INICIAR.cmd
```

Preparación y ejecución manual desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe iniciar.py
```

Si Python está disponible como `py`, cambia el primer comando por `py -3 -m venv .venv`.
Para elegir otro puerto o evitar abrir automáticamente el navegador:

```powershell
.\.venv\Scripts\python.exe iniciar.py --puerto 5050
.\.venv\Scripts\python.exe iniciar.py --sin-navegador
```

## Ejecutar backend y frontend por separado

Ejecuta ambos comandos desde la carpeta raíz del proyecto, cada uno en una terminal.
La preparación del entorno y las dependencias se hace una sola vez, como se indica arriba.

**Terminal 1 — backend Flask en el puerto 5000:**

```powershell
.\.venv\Scripts\python.exe iniciar.py --solo-api --puerto 5000
```

Comprueba la API en http://127.0.0.1:5000/api/salud o en http://127.0.0.1:5000/api/pacientes.
En este modo el backend no sirve páginas HTML.
Si el puerto estaba ocupado y se eligió otro, usa ese número en `--api` de la terminal 2.

**Terminal 2 — frontend independiente en el puerto 5500:**

```powershell
.\.venv\Scripts\python.exe frontend\servidor.py --puerto 5500 --api http://127.0.0.1:5000
```

Abre http://127.0.0.1:5500. El servidor de desarrollo entrega exclusivamente el frontend
y reenvía `/api/...` al backend configurado. No necesita Node, npm ni servicios externos.
Las mismas pantallas y el mismo cliente HTTP funcionan tanto en modo conjunto como separado.

Para desarrollar el backend con recarga automática también puedes usar:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_api run --debug --port 5000
```

## Archivos del proyecto

```text
05_Aplicacion_Web/
├── backend/
│   ├── __init__.py        Factoría Flask y manejo de errores
│   ├── config.py          Rutas del programa y campos de la API
│   ├── database.py        Conexiones, esquema SQLite y ejemplos iniciales
│   ├── rutas.py           Endpoints REST
│   ├── servicios.py       Operaciones y transacciones
│   ├── repositorios.py    Consultas SQL parametrizadas
│   ├── validaciones.py    Validaciones de negocio
│   ├── errores.py         Errores controlados de la aplicación
│   └── utilidades.py      Normalización de texto
├── frontend/
│   ├── index.html, pacientes.html, consulta.html, centros.html, areas.html, camas.html
│   ├── css/style.css
│   ├── assets/hospital.svg
│   ├── js/api.js          Cliente HTTP sin almacenamiento local
│   ├── js/crud.js         Formularios y acciones de las tablas
│   ├── js/camas.js        Habitaciones, disponibilidad y asignación de camas
│   ├── js/ui.js           Formato, avisos y utilidades de presentación
│   ├── js/inicio.js, pacientes.js, consulta.js, centros.js, areas.js
│   └── servidor.py        Servidor de desarrollo independiente con proxy
├── data/hospital.db       Base de datos del código fuente
├── tests/                 Pruebas de backend, integración y ejecutable
├── iniciar.py             Inicio local con Waitress y apertura del navegador
├── INICIAR.cmd            Inicio automático para Windows
├── app.py                 Entrada compatible con la versión anterior
├── crear_portable.py      Construye los ZIP del ejecutable y del código fuente
├── requirements.txt       Flask y Waitress
├── requirements-build.txt Dependencias de empaquetado
├── API.md                 Contrato y ejemplos de la API
├── Hospital_Portable.zip  Programa para Windows de 64 bits
└── Hospital_Codigo_Fuente.zip  Backend, frontend y código editable
```

## Datos, respaldos y portabilidad

La versión fuente guarda los registros en `data/hospital.db` de la raíz del proyecto.
La versión portable usa `data/hospital.db` junto a `Hospital.exe`; ambas son copias independientes.
Al instalar el programa por primera vez se cargan 3 pacientes, 2 centros, 4 áreas, 2 habitaciones
y 4 camas de ejemplo. Si la base viene del Sprint 1, la migración conserva los registros y agrega
las columnas de triaje y las tablas de habitaciones y camas.
Si borras registros, no se vuelven a insertar al reiniciar.

Para trasladar el programa con sus registros actualizados, apágalo y comprime toda la
carpeta portable, incluyendo `Hospital.exe` y `data`. El ZIP entregado es una copia del
momento en que se generó; no se actualiza solo. Si envías únicamente el EXE se creará
una base nueva con los ejemplos. Para respaldar datos, copia el `.db` con el programa apagado.
Los datos de la antigua versión basada en el navegador no se importan automáticamente.

Está preparado para el uso local académico del Sprint 2. No incluye autenticación de usuarios.

## Construir las entregas después de cambiar el código

Cierra el ejecutable portable antes de reconstruirlo y ejecuta:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe crear_portable.py
```

Genera el ejecutable en `dist/Hospital_Portable/Hospital.exe`, el ZIP portable y el ZIP del código fuente.
Si ya existe la base del portable, se conserva; en la primera construcción se copia la base del código
fuente o se crean los ejemplos. El ZIP del código fuente incluye una copia coherente de su propia base.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests\verificar_portable.py
```

Las pruebas comprueban CRUD, validaciones del servidor, triaje y orden por gravedad, habitaciones y
camas, disponibilidad por centro y área, asignación y liberación de camas, búsquedas SQL, duplicados
concurrentes, relaciones y borrado en cascada, persistencia, archivos privados y frontend/backend
en dos servidores.
La segunda prueba extrae el ZIP en otra ubicación e inicia el EXE sin Python en PATH, comprobando
recursos, puertos ocupados y conservación de datos al reiniciar.
