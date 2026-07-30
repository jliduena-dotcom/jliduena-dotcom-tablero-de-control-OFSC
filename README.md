# Dashboard Avance Operativo — OFSC

Arquitectura híbrida: tu automatización local en Windows sigue exactamente
igual, y ahora además alimenta una app en Streamlit publicada gratis.

```
este_repo/
├── generar_dashboard.py                  # Motor: lee Excel/xlsb, clasifica, genera HTML y CSV
├── iniciar_dashboard.bat                 # Lanzador Windows (sin cambios)
├── dashboard_avance_operativo.html       # Salida HTML (Chart.js) — respaldo / GitHub Pages
├── Repositorio_OFSC_Diario_Avance.xlsx   # Tu Excel fuente (NO se sube a git)
├── RM_Comercial.xlsb                     # Tu Excel comercial fuente (NO se sube a git)
└── proyecto_dashboard/                   # App de Streamlit
    ├── app.py                            # Lee únicamente data/dashboard_data.csv
    ├── requirements.txt
    └── data/
        └── dashboard_data.csv            # Generado automáticamente por generar_dashboard.py
```

---

## 🧠 Qué analicé de tus archivos y qué decisión tomé

1. **`generar_dashboard.py`** es el verdadero motor: lee
   `Repositorio_OFSC_Diario_Avance.xlsx` (tu export de OFSC, 181 columnas),
   lo clasifica (`clasificar_tipo`, `clasificar_franja`), lo cruza con
   `RM_Comercial.xlsb` (494,530 filas, mapea código de asesor → canal
   comercial vía `TCARGU`/`CANAL2`), y arma el HTML con los datos embebidos.

2. **`iniciar_dashboard.bat`** ejecuta
   `generar_dashboard.py --refresh --publish --watch`: refresca Power Query
   en Excel (vía `xlwings`, requiere Windows + Excel instalado), regenera el
   HTML, hace `git push` a GitHub Pages, y se queda vigilando la carpeta de
   Bases OFSC para repetir el proceso automáticamente.

3. **Decisión de arquitectura (mi recomendación, ya implementada):**
   en vez de reimplementar toda esa clasificación de nuevo en Python para
   Streamlit —lo que crearía **dos lugares** con la misma lógica de negocio
   y el riesgo de que se desincronicen con el tiempo—, modifiqué
   `generar_dashboard.py` para que, en cada ejecución, **además** exporte un
   CSV limpio y legible (`proyecto_dashboard/data/dashboard_data.csv`) que
   la app de Streamlit simplemente lee. La lógica de negocio sigue viviendo
   en un único archivo: `generar_dashboard.py`.

### Cambios exactos hechos en `generar_dashboard.py`
- Nueva función `exportar_csv_streamlit(df)`: toma el `df` que el script ya
  clasificó (no repite ningún cálculo) y escribe el CSV.
- Se llama automáticamente dentro de `generar()`, justo después del cruce
  con RM Comercial.
- `publicar()` ahora también hace `git add` del CSV de Streamlit (además del
  HTML), para que un solo commit/push actualice ambas publicaciones.
- **No cambié `iniciar_dashboard.bat`** — sigue funcionando exactamente
  igual, con los mismos flags.

---

## ⚠️ Lo que NO cambia (y por qué es importante que lo sepas)

- El refresco de Power Query (`xlwings`, `wb.api.RefreshAll()`) y el modo
  `--watch` (monitoreo de carpetas) son **automatización de escritorio
  Windows**. Necesitan Excel instalado y solo funcionan en tu PC (o un
  servidor Windows). **No pueden correr dentro de Streamlit Community
  Cloud**, que es un contenedor Linux sin Excel.
- Por eso la arquitectura queda así: **tu PC sigue siendo la única que
  produce datos frescos** (como hoy). Streamlit Cloud solo **sirve** esos
  datos ya procesados — nunca los genera.
- **No subo `Repositorio_OFSC_Diario_Avance.xlsx` ni `RM_Comercial.xlsb` al
  repo.** Son pesados (3.5 MB y 23 MB), cambian a diario, y ya quedaron
  resumidos en el CSV de ~2,700 filas. Súbelos a git sería lento e
  innecesario — el CSV ya contiene todo lo que Streamlit necesita
  (incluido el canal ya cruzado con RM Comercial).

---

## 🚀 Flujo de trabajo del día a día (después de configurar todo una vez)

1. Ejecutas `iniciar_dashboard.bat` como siempre.
2. `generar_dashboard.py` refresca el Excel, regenera el HTML **y** el CSV
   de Streamlit.
3. `publicar()` hace commit + push de ambos archivos al repo.
4. GitHub Pages sirve el HTML actualizado (igual que hoy).
5. Streamlit Community Cloud detecta el push y **redepliega solo la app**
   (no necesitas hacer nada ahí) — a los pocos segundos, el dashboard en
   internet ya muestra el CSV nuevo.

---

## 🛠️ Configuración inicial (una sola vez)

### 1. Crear el repositorio (recomendado: privado)
Dado que `RM_Comercial` involucra códigos de asesor comercial y el detalle
por técnico incluye nombres reales, te recomiendo un **repositorio privado**
en GitHub, no público.

```bash
cd este_repo               # la carpeta que contiene generar_dashboard.py
git init
git add generar_dashboard.py iniciar_dashboard.bat dashboard_avance_operativo.html
git add proyecto_dashboard/app.py proyecto_dashboard/requirements.txt proyecto_dashboard/data/dashboard_data.csv
git commit -m "Setup inicial dashboard + Streamlit"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

> Asegúrate de que tu `.gitignore` excluya los Excel/xlsb fuente:
> ```
> Repositorio_OFSC_Diario_Avance.xlsx
> RM_Comercial.xlsb
> ```

### 2. Desplegar en Streamlit Community Cloud (gratis)
1. Entra a https://share.streamlit.io/ y conéctate con tu cuenta de GitHub.
2. "New app" → selecciona tu repositorio y rama `main`.
3. **Main file path:** `proyecto_dashboard/app.py` (¡importante! no es
   `app.py` a secas, porque vive en la subcarpeta).
4. Deploy. En 1–3 minutos tendrás tu URL pública
   (`https://tu-app.streamlit.app`).
5. **Privacidad:** en el panel de la app, en "Settings → Sharing", puedes
   restringirla a una lista de correos autorizados si los datos son
   sensibles (recomendado dado que hay nombres de técnicos y códigos
   comerciales).

### 3. (Opcional) Publicar el HTML en GitHub Pages
Si quieres mantener también el HTML como respaldo visual idéntico:
**Settings → Pages** en el repo → rama `main` → carpeta `/ (root)`.
La URL quedará como `https://TU_USUARIO.github.io/TU_REPO/dashboard_avance_operativo.html`.

---

## 🧪 Cómo lo validé antes de entregártelo

- Ejecuté `generar_dashboard.py` (sin `--refresh`, que requiere Excel/Windows)
  contra tus archivos reales: procesó **2,674 órdenes** válidas de las 3,986
  filas del Excel, cruzó **1,293 registros** con canal desde RM Comercial, y
  generó correctamente tanto el HTML como el CSV.
- Corrí `proyecto_dashboard/app.py` con ese CSV real: la app levanta sin
  errores y todas las pestañas (Dashboard, Proyección, Resumen Ejecutivo,
  Control Técnicos) renderizan con tus datos reales.

---

## 📌 Limitación pendiente: pestaña "Comparativa Diaria"

Tu script tiene una función completa `calcular_comparativa()` (avance
acumulado hora a hora vs. benchmark histórico) pensada para un archivo
`comparativa_diaria_template.html` que **no me llegó** — no existe en los
archivos que subiste. Por eso no la migré a Streamlit todavía.

Si me compartes ese template (o simplemente confirmas qué visualizaciones
esperas ver: avance acumulado por hora, comparación entre días, etc.), la
agrego como una quinta pestaña reutilizando esa misma función que ya está
escrita y funcionando.

## 🔧 Otras recomendaciones críticas

- **`RM_Comercial.xlsb` tarda ~44 segundos en leerse** (494,530 filas vía
  `pyxlsb`). Esto solo afecta a la ejecución local de `generar_dashboard.py`
  (una vez al día), no a Streamlit Cloud, que nunca toca ese archivo. Si en
  el futuro este tiempo te molesta, se puede optimizar leyendo solo el
  rango de columnas necesario con una librería más rápida, o cacheando el
  mapeo `TCARGU→CANAL2` entre corridas.
- El estado `"Suspendido"` apareció en tus datos reales y no estaba en la
  muestra original — ya lo verifiqué y no rompe ninguna métrica (no forma
  parte de "gestionado" ni de "efectividad", igual que en tu lógica
  original).
