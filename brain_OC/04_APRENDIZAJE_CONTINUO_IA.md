# Aprendizaje Continuo IA — [NOMBRE_PROYECTO]

<- Volver al [[00_TABLERO_PRINCIPAL|Tablero Principal]]

**[NOMBRE_PROYECTO]** no es un software estático. Su núcleo de Inteligencia Artificial debe evolucionar absorbiendo el *Know-How* del equipo en tiempo real. Para lograrlo sin interrumpir la operación, implementamos una **Arquitectura de Aprendizaje en la Sombra (Shadow Learning / RAG Enriquecido)**.

---

## 1. El Concepto: "La Puerta Trasera Silenciosa"

**Premisa:** Cada vez que un operador resuelve exitosamente un caso, [NOMBRE_PROYECTO] absorbe esa resolución, la vectoriza y se vuelve un poco más inteligente para el próximo caso similar.

### ¿Por qué RAG y no Fine-Tuning?

| Estrategia | Cuándo usarla | Costo | Aplicable |
|---|---|---|---|
| Fine-Tuning | Dominio muy específico, datos estáticos | Alto (GPU, tiempo) | ❌ No (textos dinámicos) |
| **RAG (Retrieval Augmented)** | **Conocimiento actualizable, fuentes externas** | **Bajo-Medio** | **✅ Sí** |
| Prompt Engineering | Ajustes rápidos sin reentrenamiento | Mínimo | ✅ Sí |
| Agentes + Herramientas | Flujos multi-paso con decisiones | Medio | ✅ Sí |

---

## 2. El Pipeline de Aprendizaje Paso a Paso

### Paso 1 — El Hook (Disparador)
Se instala un Webhook o trigger en la base de datos del sistema.

**Evento que dispara el pipeline:**
```sql
-- Trigger: cuando un caso pasa a estado CERRADO/RESUELTO
AFTER UPDATE ON casos
WHEN (NEW.estado = 'CERRADO' AND OLD.estado != 'CERRADO')
```

### Paso 2 — El Evento Silencioso
Cuando un caso pasa a estado `CERRADO`, el sistema captura el par:
```
[Descripción original del problema] <——> [Respuesta validada y aprobada por el experto]
```

### Paso 3 — El Ingestor de Aprendizaje (Shadow Worker)
El Shadow Worker recibe el par y lo pre-procesa:
- Limpia el texto (sin HTML, sin datos personales identificables)
- Agrega metadatos: industria del cliente, tipo de solicitud, score de satisfacción

### Paso 4 — Vectorización Nocturna
A las **[hora, ej: 2:00 AM]**, el sistema procesa todos los casos resueltos del día:
```python
# Pipeline nocturno simplificado
casos_del_dia = obtener_casos_cerrados_hoy()
for caso in casos_del_dia:
    embedding = modelo_embeddings.encode(caso.descripcion + caso.respuesta)
    vector_db.upsert(id=caso.id, vector=embedding, metadata=caso.metadatos)
```

### Paso 5 — Uso al Día Siguiente
Cuando entra un nuevo caso:
1. Se vectoriza la descripción del nuevo caso.
2. Se buscan los **Top-[3-5] casos históricos más similares** en la base vectorial.
3. Se inyectan como contexto al prompt del Agente IA.
4. El Agente genera un borrador con la calidad y estilo de los expertos del equipo.

```
PROMPT AL AGENTE:
"Redacta la respuesta para este caso nuevo. 
Usa el mismo tono, lenguaje y estructura que el equipo usó 
en estos [N] casos similares del pasado: 
[Ejemplo 1], [Ejemplo 2], [Ejemplo 3]."
```

---

## 3. El Data Flywheel (Efecto Compuesto)

```
Más casos procesados
        ↓
Más datos de calidad en memoria vectorial
        ↓
IA genera mejores borradores iniciales
        ↓
Menos tiempo de corrección humana
        ↓
Se procesan más casos con el mismo equipo
        ↓
[Vuelve al inicio]
```

Este ciclo garantiza que el sistema no dependa solo de reglas estáticas, sino también de la **jurisprudencia interna y el criterio dinámico** del equipo real.

---

## 4. Configuración del Motor de IA

| Parámetro | Valor / Configuración | Propósito |
|---|---|---|
| Modelo base | [claude-sonnet / gpt-4o / llama3] | Generación de borradores |
| Modelo de embeddings | [text-embedding-3-small / etc.] | Vectorización de documentos |
| Vector DB | [pgvector / Pinecone / Weaviate] | Almacenamiento de memorias |
| Top-K retrieval | [3-5 documentos similares] | Contexto RAG inyectado al prompt |
| Temperature | [0.2 para tareas de redacción] | Control de creatividad vs precisión |
| Max tokens respuesta | [2048 / 4096] | Límite de longitud del borrador |
| Ventana de contexto | [100K / 200K tokens] | Máximo contexto inyectable |

---

## 5. Métricas de Calidad del Modelo

| Métrica | Descripción | Objetivo |
|---|---|---|
| Tasa de aceptación de borrador | % de borradores IA aprobados sin modificación | [>60%] |
| Edición promedio por borrador | Número de cambios que hace el operador | [<5 cambios] |
| Tiempo de revisión | Tiempo promedio del operador para revisar un borrador | [<3 min] |
| Score de relevancia RAG | Similitud coseno del contexto recuperado | [>0.75] |

---

## 6. Consideraciones de Privacidad

> ⚠️ **Importante:** Los datos usados para el aprendizaje deben anonimizarse antes de vectorizarse.

- Los nombres, cédulas y datos personales de los solicitantes deben ser reemplazados por tokens (`[PERSONA_1]`, `[EMPRESA_A]`) antes de generar el embedding.
- Los vectores almacenados no deben permitir reconstruir el dato original.
- Cumplir con **Ley 1581 de 2012** (Colombia) o la normativa de protección de datos aplicable al país del cliente.
