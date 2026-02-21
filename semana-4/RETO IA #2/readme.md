# Monitor de Inventario - EcoMarket 

## Traza de Red (Reto 1)
| Consulta | Header Enviado | Status | Acción | Intervalo |
| :--- | :--- | :--- | :--- | :--- |
| #1 | (Vacío) | 200 OK | Guarda ETag: "abc123" | 5s |
| #2 | If-None-Match: "abc123" | 304 | Mantiene UI | 7.5s (Backoff) |
| #3 | If-None-Match: "abc123" | 304 | Mantiene UI | 11.25s (Backoff) |
| #4 | If-None-Match: "abc123" | 200 OK | Cambia ETag a "def456" | 5s (Reset) |

> **Eficiencia ETag:** Es superior a comparar datos completos porque el servidor solo valida un "hash" o etiqueta. Si no hay cambios, no se descarga el cuerpo de la respuesta, ahorrando ancho de banda y procesamiento en el cliente.