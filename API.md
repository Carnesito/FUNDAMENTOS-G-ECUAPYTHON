# API REST del Sistema de Gestión Hospitalaria

Base local habitual: `http://127.0.0.1:5000/api`. Cuerpo de solicitudes y respuestas: JSON UTF-8.
No se requiere abrir el frontend para utilizar la API. La base de datos es SQLite.

## Endpoints

Los recursos válidos son `pacientes`, `centros`, `areas`, `habitaciones` y `camas`.

| Método | Ruta | Resultado |
|---|---|---|
| GET | `/api/salud` | Estado y versión del backend |
| GET | `/api/resumen` | Totales calculados en SQLite, incluido el estado de las camas |
| GET | `/api/disponibilidad` | Camas totales, libres, ocupadas y en mantenimiento por centro y área |
| GET | `/api/{recurso}` | Lista: `{"registros": [...], "total": 3}` |
| GET | `/api/{recurso}/{id}` | Un registro: `{"registro": {...}}` |
| POST | `/api/{recurso}` | Crea un registro; 201 y cabecera Location |
| PUT | `/api/{recurso}/{id}` | Reemplaza sus campos editables; 200 |
| DELETE | `/api/{recurso}/{id}` | Elimina; 204 sin cuerpo |
| GET | `/api/datos` | Lectura conjunta para integraciones anteriores |

POST y PUT devuelven únicamente el registro confirmado por la transacción. El navegador vuelve a
consultar las listas que necesita; el backend no envía toda la base en cada escritura.
PUT requiere todos los campos editables, igual que POST. Los ID los genera el servidor.
Los campos internos como `nombre_clave`, `numero_clave` y `codigo_clave` nunca se exponen.

## Filtros ejecutados en SQL

| Ejemplo | Comportamiento |
|---|---|
| `/api/pacientes?cedula=0951234567` | Coincidencia exacta de cédula |
| `/api/pacientes?apellidos=vera` | Coincidencia parcial en nombres y apellidos |
| `/api/pacientes?triaje=Nivel%20I` | Pacientes de un nivel de triaje |
| `/api/pacientes?q=fernanda` | Busca en cédula, nombres, teléfono y motivo |
| `/api/centros?q=norte` | Busca en nombre y dirección |
| `/api/areas?centroId=c1` | Áreas de un centro |
| `/api/areas?q=emergencia` | Busca en nombre del área y de su centro |
| `/api/habitaciones?centroId=c1` | Habitaciones de las áreas de un centro |
| `/api/habitaciones?areaId=a1` | Habitaciones de un área |
| `/api/camas?estado=Disponible` | Camas libres |
| `/api/camas?centroId=c1&areaId=a1` | Camas de un área dentro de un centro |
| `/api/camas?sinPaciente=1` | Camas sin paciente asignado |
| `/api/camas?q=H-01` | Busca en código, habitación, área, centro y paciente |
| `/api/disponibilidad?centroId=c1&areaId=a1` | Resumen filtrado de capacidad |

La búsqueda de texto ignora mayúsculas y tildes. Los valores se parametrizan;
`%` y `_` se interpretan literalmente en las búsquedas parciales.
Los centros incluyen `areasCount`; las áreas incluyen `centroNombre`; las habitaciones incluyen
`areaNombre`, `centroNombre`, `camasCount` y `disponiblesCount`; las camas incluyen
`habitacionNumero`, `piso`, `areaNombre`, `centroNombre` y `pacienteNombre`.

La lista de pacientes se ordena por gravedad (Nivel I, II, III, IV y sin asignar) y luego por nombre.

## Campos

**Pacientes:** `cedula`, `nombres`, `nacimiento`, `telefono`, `triaje`, `motivo`, `signos`,
`triaje_fecha`. Cédula única de 10 dígitos; nombre de al menos 3 caracteres; fecha ISO
`AAAA-MM-DD` entre 1900 y hoy; teléfono de 7 a 10 dígitos. Triaje admite cadena vacía o
`Nivel I` a `Nivel IV`. `motivo` y `signos` admiten hasta 200 caracteres; `triaje_fecha` acepta
`AAAA-MM-DD HH:MM` o `AAAA-MM-DDTHH:MM`. La respuesta incluye `cama` como solo lectura: se
calcula con la cama realmente asignada en el catálogo y no se puede escribir directamente.
`camaHeredada` conserva la cama escrita como texto libre en el Sprint 1 cuando ese código no
existe en el catálogo; el paciente sigue disponible para recibir una cama real y, al asignarla,
el texto heredado se limpia.

**Centros:** `nombre`, `direccion`, `telefono`. Todos obligatorios; nombre de al menos
3 caracteres y único sin distinguir mayúsculas ni tildes; teléfono de 7 a 10 dígitos.

**Áreas:** `centroId`, `nombre`, `tipo`. Todos obligatorios; el centro debe existir.
El nombre no puede repetirse en el mismo centro. Tipos: `Emergencia`, `Consulta externa`,
`Hospitalización`, `Quirófano`, `Laboratorio`, `Imágenes`.

**Habitaciones:** `areaId`, `numero`, `piso`, `tipo`. Todos obligatorios; el área debe existir
y el número no puede repetirse dentro del área. Tipos: `Individual`, `Doble`, `UCI`,
`Aislamiento`, `Observación`. Al eliminar un área o un centro se eliminan sus habitaciones.

**Camas:** `habitacionId`, `codigo`, `estado`, `pacienteId`, `observacion`. El código es único
en todo el hospital (sin distinguir mayúsculas ni tildes). Estados: `Disponible`, `Ocupada`,
`Mantenimiento`. Si se envía `pacienteId`, la cama pasa a `Ocupada` y el paciente no puede tener
otra cama; si se deja vacío, una cama ocupada vuelve a `Disponible`. Al eliminar la cama, la
habitación, el área, el centro o el paciente, la referencia del paciente se libera en la misma
transacción.

## Ejemplo desde PowerShell

```powershell
$api = "http://127.0.0.1:5000/api"
Invoke-RestMethod "$api/resumen"
Invoke-RestMethod "$api/camas?estado=Disponible"
Invoke-RestMethod "$api/disponibilidad"

$datos = @{
    cedula = "1234567890"
    nombres = "Paciente de prueba"
    nacimiento = "1995-05-10"
    telefono = "0991234567"
    triaje = "Nivel II"
    motivo = "Dolor abdominal"
    signos = "TA 120/80 · FC 88 · T 36.8 °C"
    triaje_fecha = "2026-11-23T08:30"
}
$creado = Invoke-RestMethod "$api/pacientes" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes(($datos | ConvertTo-Json)))
$idPaciente = $creado.registro.id

$cama = @{ habitacionId = "h1"; codigo = "E-10"; estado = "Disponible"; pacienteId = $idPaciente; observacion = "" }
$asignada = Invoke-RestMethod "$api/camas" -Method Post -ContentType "application/json" -Body ($cama | ConvertTo-Json)
$asignada.registro.estado   # Ocupada
Invoke-RestMethod "$api/pacientes/$idPaciente"  # cama = E-10
```

## Errores y límites

Formato: `{"error": "Mensaje", "campo": "cedula"}`. `campo` puede ser nulo o estar ausente.

- 400: datos o campos inválidos.
- 403: origen de escritura no permitido.
- 404: recurso o registro inexistente.
- 405: método HTTP no permitido.
- 409: cédula, nombre, número de habitación o código de cama duplicado.
- 413: solicitud de más de 32 KiB.
- 415: el cuerpo no tiene tipo JSON.
- 503: base de datos temporalmente no disponible.

El servidor confirma o revierte cada escritura completa. Eliminar un centro borra sus áreas y,
en cascada, sus habitaciones y camas. Las respuestas API no se guardan en la caché HTTP.
La API se ejecuta localmente, sin autenticación, para el alcance académico del Sprint 2.
