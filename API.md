# API REST del Sistema de Gestión Hospitalaria

Base local habitual: `http://127.0.0.1:5000/api`. Cuerpo de solicitudes y respuestas: JSON UTF-8.
No se requiere abrir el frontend para utilizar la API. La base de datos es SQLite.

## Endpoints

Los recursos válidos son `pacientes`, `centros` y `areas`.

| Método | Ruta | Resultado |
|---|---|---|
| GET | `/api/salud` | Estado y versión del backend |
| GET | `/api/resumen` | Totales calculados en SQLite |
| GET | `/api/{recurso}` | Lista: `{"registros": [...], "total": 3}` |
| GET | `/api/{recurso}/{id}` | Un registro: `{"registro": {...}}` |
| POST | `/api/{recurso}` | Crea un registro; 201 y cabecera Location |
| PUT | `/api/{recurso}/{id}` | Reemplaza sus campos editables; 200 |
| DELETE | `/api/{recurso}/{id}` | Elimina; 204 sin cuerpo |
| GET | `/api/datos` | Lectura conjunta para integraciones anteriores |

POST y PUT devuelven únicamente el registro confirmado por la transacción. El navegador vuelve a
consultar las listas que necesita; el backend no envía toda la base en cada escritura.
PUT requiere todos los campos obligatorios, igual que POST. Los ID los genera el servidor.
Los campos internos como `nombre_clave` nunca se exponen en las respuestas.

## Filtros ejecutados en SQL

| Ejemplo | Comportamiento |
|---|---|
| `/api/pacientes?cedula=0951234567` | Coincidencia exacta de cédula |
| `/api/pacientes?apellidos=vera` | Coincidencia parcial en nombres y apellidos |
| `/api/pacientes?q=fernanda` | Busca en cédula, nombres y teléfono |
| `/api/centros?q=norte` | Busca en nombre y dirección |
| `/api/areas?centroId=c1` | Áreas de un centro |
| `/api/areas?q=emergencia` | Busca en nombre del área y nombre de su centro |

La búsqueda de texto ignora mayúsculas y tildes. Los valores se parametrizan;
`%` y `_` se interpretan literalmente en las búsquedas parciales.
Los centros incluyen `areasCount`; las áreas incluyen `centroNombre`.

## Campos

**Pacientes:** `cedula`, `nombres`, `nacimiento`, `telefono`, `triaje`, `cama`.
Cédula única de 10 dígitos; nombre de al menos 3 caracteres; fecha ISO `AAAA-MM-DD`
entre 1900 y hoy; teléfono de 7 a 10 dígitos. Triaje y cama son opcionales.
Triaje admite cadena vacía o `Nivel I`, `Nivel II`, `Nivel III`, `Nivel IV`.

**Centros:** `nombre`, `direccion`, `telefono`. Todos obligatorios; nombre de al menos
3 caracteres y único sin distinguir mayúsculas ni tildes; teléfono de 7 a 10 dígitos.

**Áreas:** `centroId`, `nombre`, `tipo`. Todos obligatorios; el centro debe existir.
El nombre no puede repetirse en el mismo centro. Tipos: `Emergencia`, `Consulta externa`,
`Hospitalización`, `Quirófano`, `Laboratorio`, `Imágenes`.

## Ejemplo desde PowerShell

```powershell
$api = "http://127.0.0.1:5000/api"
Invoke-RestMethod "$api/resumen"
Invoke-RestMethod "$api/pacientes?apellidos=vera"

$datos = @{
    cedula = "1234567890"
    nombres = "Paciente de prueba"
    nacimiento = "1995-05-10"
    telefono = "0991234567"
    triaje = "Nivel II"
    cama = "A-01"
}
$creado = Invoke-RestMethod "$api/pacientes" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes(($datos | ConvertTo-Json)))
$id = $creado.registro.id

$datos.cama = "A-02"
Invoke-RestMethod "$api/pacientes/$id" -Method Put -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes(($datos | ConvertTo-Json)))
Invoke-RestMethod "$api/pacientes/$id"
Invoke-RestMethod "$api/pacientes/$id" -Method Delete
```

## Errores y límites

Formato: `{"error": "Mensaje", "campo": "cedula"}`. `campo` puede ser nulo o estar ausente.

- 400: datos o campos inválidos.
- 403: origen de escritura no permitido.
- 404: recurso o registro inexistente.
- 405: método HTTP no permitido.
- 409: cédula o nombre duplicado.
- 413: solicitud de más de 32 KiB.
- 415: el cuerpo no tiene tipo JSON.
- 503: base de datos temporalmente no disponible.

El servidor confirma o revierte cada escritura completa. Eliminar un centro borra sus áreas
por clave foránea con ON DELETE CASCADE. Las respuestas API no se guardan en la caché HTTP.
La API se ejecuta localmente, sin autenticación, para el alcance académico del Sprint 1.
