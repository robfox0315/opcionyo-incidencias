# 🧑‍💼 Guía para presentar a gerencia

Esta guía explica, en lenguaje simple, **qué muestra cada pestaña** y **cómo
contar la historia** en una reunión de gerencia. Pensada para que cualquiera
pueda presentar el dashboard sin ser técnico.

---

## 🎬 Guion de presentación (5 minutos)

1. **Abre en "📊 Resumen".** Frase de apertura:
   > "En mayo tuvimos **280 incidencias técnicas**. El dato que más pesa: el
   > **56% cerró sin una respuesta registrada**. Ese es el problema a resolver."

2. **Pasa a "🎯 Sin Respuesta" → mira el gráfico de fuga por categoría.**
   > "La fuga no es pareja: **'IT - Soporte técnico' cierra 93% sin respuesta**.
   > Ahí está la causa raíz, no en todo el volumen."

3. **Señala el ranking de reincidencia.**
   > "Y se concentra en pocos: **Diana Sánchez, una especialista, repite 11 veces**.
   > Con acciones 1-a-1 al top de la lista cortamos buena parte del problema."

4. **Salta a "📡 Telemetría" → Incidencias por tipo.**
   > "Del lado de plataforma, **2 tipos (Métricas de red y Errores JS) explican el
   > ~84%** de los eventos. Y de las **pruebas técnicas, 69% de los casos 'Malo'
   > mejoraron** tras seguimiento: el plan funciona."

5. **Cierra en "💡 Insights & Recomendaciones".**
   > "Aquí está el resumen automático con la acción sugerida para cada hallazgo.
   > Propongo estas 3 prioridades para junio…"

---

## 📋 Qué muestra cada pestaña

| Pestaña | En una frase | Métrica estrella |
|---|---|---|
| 📊 **Resumen** | La foto del mes | % sin respuesta, tiempo a cierre **en días** |
| 🎯 **Sin Respuesta** | Dónde y en quién se concentra la falta de respuesta | Tasa de fuga por categoría · top reincidente |
| 🔁 **Reincidencia** | Quién abre tickets una y otra vez | Contactos con >1 ticket |
| 📁 **Distribuciones** | Cómo se reparten los tickets | Categoría, prioridad, estado |
| ⏱️ **SLA & Tiempos** | Si cumplimos los plazos | % ANS a tiempo · días a cierre |
| 🎓 **Atención Especialistas** | Qué tan rápido atendemos a los coaches | ANS + días a resolución |
| 🔎 **Explorador** | Ver/descargar cualquier corte | Tabla filtrable |
| 📡 **Telemetría** | Salud técnica de las sesiones | Incidencias por tipo · pruebas |
| 💡 **Insights** | Conclusiones + acciones automáticas | Hallazgos críticos/alertas |

---

## 🔑 Glosario rápido (para no técnicos)

- **Sin respuesta:** el ticket se cerró sin que quede registrada una respuesta al
  cliente/especialista. No siempre significa abandono, pero sí falta de registro.
- **ANS (Acuerdo de Nivel de Servicio):** el plazo pactado para responder o cerrar.
  "A tiempo" = dentro del plazo; "Vencido" = fuera.
- **Reincidencia:** un mismo contacto que vuelve a abrir tickets.
- **P90:** el 90% de los casos está por debajo de ese valor (más representativo que
  el promedio cuando hay casos extremos).
- **Especialista (E):** coach interno de Opción Yo (correo @opcionyo). El resto son
  clientes externos.
- **Telemetría:** señales técnicas que registra la plataforma durante las sesiones
  (caídas de conexión, recargas, errores de JavaScript, etc.).

---

## ⚠️ Honestidad del dato (decirlo si preguntan)

- El nombre del **especialista no se extrae del texto** del ticket (no aparece de
  forma fiable). La reincidencia se mide por el **contacto asociado**.
- **No hay duración real de la 1ª respuesta** en el export actual; se mide
  cumplimiento del ANS y tiempo total a resolución. Para el "tarda X en atender"
  exacto, hay que re-exportar de HubSpot esa propiedad.
