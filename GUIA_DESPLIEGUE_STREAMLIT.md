# 🚀 Guía de despliegue paso a paso (a prueba de errores)

Esta guía te lleva de **cero a dashboard en línea** sin usar línea de comandos.
Tiempo estimado: **10–15 minutos**. Solo necesitas un navegador.

> 💡 Vas a hacer 2 cosas: (A) subir la carpeta a GitHub, (B) conectarla a
> Streamlit. Sigue los pasos en orden y no te saltes ninguno.

---

## ✅ Antes de empezar (checklist)

- [ ] Tienes el archivo **`opcionyo-incidencias.zip`** descargado y **descomprimido**
      (debe quedar una carpeta con `app.py`, `data_loader.py`, etc.).
- [ ] Tienes una cuenta de **GitHub** (si no, créala gratis en
      [github.com](https://github.com) → *Sign up*).
- [ ] Usarás el mismo correo para GitHub y para Streamlit (más fácil).

---

## PARTE A · Subir el proyecto a GitHub

### Paso 1 — Crear un repositorio NUEVO y PRIVADO
1. Entra a [github.com](https://github.com) e inicia sesión.
2. Arriba a la derecha pulsa **+** → **New repository**.
3. En *Repository name* escribe: `opcionyo-incidencias`
4. Marca la opción **Private** ✅ (importante: los datos tienen correos de clientes).
5. **No** marques "Add a README" (ya tenemos uno).
6. Pulsa **Create repository**.

### Paso 2 — Subir los archivos (arrastrar y soltar)
1. En la página del repo recién creado verás un enlace que dice
   **"uploading an existing file"**. Pulsa ahí.
   *(Si no lo ves: pestaña **Add file** → **Upload files**.)*
2. Abre la carpeta descomprimida en tu computadora.
3. **Selecciona TODOS los archivos y carpetas** de adentro
   (`app.py`, `data_loader.py`, `requirements.txt`, `README.md`,
   `GUIA_DESPLIEGUE_STREAMLIT.md`, `.gitignore`, la carpeta `.streamlit/`
   y la carpeta `data/`) y **arrástralos** a la zona que dice
   *"Drag files here"*.

   > ⚠️ **Muy importante:** arrastra el *contenido* de la carpeta, **no** la
   > carpeta `opcionyo-incidencias` entera. En GitHub deben quedar `app.py` y
   > `data_loader.py` en la raíz, no dentro de otra subcarpeta.
   >
   > Si tu explorador no muestra `.gitignore` o `.streamlit` (archivos que
   > empiezan con punto), actívalos: en **Windows** (Explorador → Vista →
   > "Elementos ocultos"); en **Mac** (pulsa `Cmd + Shift + .`).

4. Abajo, en *Commit changes*, deja el mensaje por defecto y pulsa
   **Commit changes**.
5. Espera a que termine de subir. Refresca: debes ver `app.py` en la lista.

✔️ **Verifica:** en la raíz del repo se ven `app.py`, `data_loader.py`,
`requirements.txt` y la carpeta `data`. Si `app.py` está dentro de otra
carpeta, bórralo y vuelve a subir solo el contenido.

---

## PARTE B · Conectar con Streamlit Cloud

### Paso 3 — Entrar a Streamlit
1. Ve a **[share.streamlit.io](https://share.streamlit.io)**.
2. Pulsa **Continue with GitHub** e inicia sesión.
3. La primera vez te pedirá **autorizar** a Streamlit para ver tus repos.
   Acepta. Como el repo es privado, autoriza también el acceso a repos privados.

### Paso 4 — Crear la app
1. Pulsa **Create app** (o **New app**) → elige
   **"Deploy a public app from GitHub"** / **"I have an app"**.
2. Rellena los 3 campos:
   - **Repository:** `tu-usuario/opcionyo-incidencias`
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. (Opcional) En *App URL* elige un nombre, p. ej. `opcionyo-incidencias`.
4. Pulsa **Deploy!**

### Paso 5 — Esperar el primer arranque
- Verás una pantalla con registros ("Installing requirements…").
- La **primera vez tarda 2–4 minutos** mientras instala pandas/plotly.
- Cuando termine, aparece el dashboard con las **muestras ya cargadas**.

🎉 **¡Listo!** Tu URL será algo como
`https://opcionyo-incidencias.streamlit.app`

---

## 🔄 Cómo usar y actualizar los datos

- **Para analizar un export nuevo:** en la barra lateral, sección
  *"1 · Fuente de datos"*, pulsa **Browse files** y sube tu `.xlsx` o `.csv`
  de HubSpot. El dashboard se recalcula al instante (no toca el repo).
- **Para cambiar la muestra base** (la que se ve al abrir): en GitHub, entra a
  `data/`, abre el CSV, pulsa el lápiz ✏️ o sube uno nuevo con el mismo nombre.
  Streamlit redepliega solo en ~1 minuto.

---

## 🧰 Solución de problemas (errores comunes)

| Síntoma | Causa probable | Solución |
|---|---|---|
| `Error: Main module not found app.py` | Subiste la carpeta entera, `app.py` quedó anidado | En GitHub borra todo y vuelve a subir **solo el contenido** de la carpeta |
| `ModuleNotFoundError: streamlit/plotly` | Falta o se renombró `requirements.txt` | Confirma que `requirements.txt` está en la raíz, tal cual |
| `No module named 'data_loader'` | No subiste `data_loader.py` | Súbelo a la raíz (mismo nivel que `app.py`) |
| La app abre pero sale "No hay datos" | No subiste la carpeta `data/` | Sube `data/` o carga un archivo desde la barra lateral |
| No veo `.streamlit` ni `.gitignore` al subir | Archivos ocultos | Actívalos (Windows: Vista→Elementos ocultos; Mac: `Cmd+Shift+.`) |
| Streamlit no ve mi repo privado | Falta permiso | En Streamlit: *Settings → Connections → GitHub → Reboot/reauthorize* |
| Cambié un archivo y no se actualiza | Caché | En la app: menú **⋮** arriba a la derecha → **Reboot app** |

---

## 🔐 Recordatorio de privacidad
El repositorio debe ser **Privado**. Nunca subas el archivo
`.streamlit/secrets.toml` (ya está excluido en `.gitignore`). Si en el futuro
agregas tokens o claves, van en *Streamlit → Settings → Secrets*, **no** al repo.
