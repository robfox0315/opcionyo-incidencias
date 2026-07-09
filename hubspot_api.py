"""
hubspot_api.py
------------------------------------------------------------------
Cliente de la API de HubSpot para el Dashboard de Incidencias Técnicas.

Trae los tickets del pipeline "Problemas técnicos" EN VIVO y los mapea al
MISMO esquema que usa el dashboard, para que todos los KPIs se calculen igual
sin importar si la fuente es un archivo o la API.

Seguridad: el token NUNCA se escribe en el código. Se pasa como argumento
(la app lo lee de st.secrets["HUBSPOT_TOKEN"]).

Ventaja clave vs archivo: la API sí trae el TIEMPO REAL de primera respuesta
y de cierre (en ms), además de fecha de creación, propietario y fuente.
"""
from __future__ import annotations

import time
import pandas as pd
import requests

API = "https://api.hubapi.com"
PIPELINE_INCIDENCIAS = "111962122"      # pipeline "Problemas técnicos"
TIMEOUT = 30

# Propiedades internas de HubSpot que pedimos (nombres API, no de display).
PROPIEDADES = [
    "subject", "content", "hs_pipeline", "hs_pipeline_stage",
    "hs_ticket_priority", "hs_ticket_category", "hs_resolution",
    "createdate", "closed_date", "hs_lastmodifieddate",
    "hs_time_to_first_response", "hs_time_to_close",
    "source_type", "hubspot_owner_id",
]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ----------------------------------------------------------------------
# PRUEBA DE CONEXIÓN
# ----------------------------------------------------------------------
def probar_conexion(token: str) -> tuple[bool, str]:
    """Devuelve (ok, mensaje). Hace una llamada mínima para validar el token."""
    if not token or not token.startswith("pat-"):
        return False, "El token está vacío o no tiene el formato 'pat-…'."
    try:
        r = requests.get(f"{API}/crm/v3/objects/tickets?limit=1",
                         headers=_headers(token), timeout=TIMEOUT)
        if r.status_code == 200:
            return True, "Conexión correcta con HubSpot."
        if r.status_code == 401:
            return False, "Token inválido o sin autorizar (401)."
        if r.status_code == 403:
            return False, ("Token sin los permisos necesarios (403). Habilita el "
                           "scope 'crm.objects.tickets.read' en la Private App.")
        return False, f"HubSpot respondió {r.status_code}: {r.text[:120]}"
    except requests.exceptions.RequestException as e:
        return False, f"No se pudo conectar con HubSpot: {e}"


# ----------------------------------------------------------------------
# CATÁLOGOS (etapas del pipeline y propietarios) para traducir IDs -> texto
# ----------------------------------------------------------------------
def _etapas_pipeline(token: str, pipeline: str) -> dict:
    """Mapa {stage_id: label} del pipeline indicado."""
    try:
        r = requests.get(f"{API}/crm/v3/pipelines/tickets/{pipeline}",
                         headers=_headers(token), timeout=TIMEOUT)
        if r.status_code != 200:
            return {}
        return {s["id"]: s["label"] for s in r.json().get("stages", [])}
    except requests.exceptions.RequestException:
        return {}


def _propietarios(token: str) -> dict:
    """Mapa {owner_id: 'Nombre Apellido'}."""
    salida, after = {}, None
    try:
        while True:
            url = f"{API}/crm/v3/owners?limit=100"
            if after:
                url += f"&after={after}"
            r = requests.get(url, headers=_headers(token), timeout=TIMEOUT)
            if r.status_code != 200:
                break
            data = r.json()
            for o in data.get("results", []):
                nombre = f"{o.get('firstName','')} {o.get('lastName','')}".strip()
                salida[o["id"]] = nombre or o.get("email", o["id"])
            after = data.get("paging", {}).get("next", {}).get("after")
            if not after:
                break
    except requests.exceptions.RequestException:
        pass
    return salida


# ----------------------------------------------------------------------
# TICKETS (con paginación y asociación a contactos)
# ----------------------------------------------------------------------
def _buscar_tickets(token: str, pipeline: str) -> list[dict]:
    """Trae todos los tickets del pipeline vía /search, paginando de 100 en 100."""
    resultados, after = [], None
    url = f"{API}/crm/v3/objects/tickets/search"
    while True:
        payload = {
            "filterGroups": [{"filters": [
                {"propertyName": "hs_pipeline", "operator": "EQ", "value": pipeline}
            ]}],
            "properties": PROPIEDADES,
            "limit": 100,
        }
        if after:
            payload["after"] = after
        r = requests.post(url, headers=_headers(token), json=payload, timeout=TIMEOUT)
        if r.status_code == 429:      # rate limit: esperar y reintentar
            time.sleep(1.0)
            continue
        r.raise_for_status()
        data = r.json()
        resultados.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return resultados


def _contactos_de_tickets(token: str, ticket_ids: list[str]) -> dict:
    """
    Devuelve {ticket_id: 'Nombre (email)'} resolviendo la asociación
    ticket->contacto y leyendo nombre/email del contacto. Best-effort:
    si algo falla, devuelve lo que pudo (el dashboard degrada con gracia).
    """
    if not ticket_ids:
        return {}
    ticket_contacto = {}
    contact_ids = set()
    # 1) asociaciones ticket -> contacto (batch de 100)
    try:
        for i in range(0, len(ticket_ids), 100):
            lote = ticket_ids[i:i + 100]
            r = requests.post(
                f"{API}/crm/v4/associations/tickets/contacts/batch/read",
                headers=_headers(token),
                json={"inputs": [{"id": t} for t in lote]}, timeout=TIMEOUT)
            if r.status_code != 200:
                continue
            for res in r.json().get("results", []):
                tid = res["from"]["id"]
                to = res.get("to", [])
                if to:
                    cid = to[0]["toObjectId"]
                    ticket_contacto[tid] = cid
                    contact_ids.add(cid)
    except requests.exceptions.RequestException:
        return {}
    # 2) leer datos de esos contactos (batch)
    contacto_info = {}
    try:
        ids = list(contact_ids)
        for i in range(0, len(ids), 100):
            lote = ids[i:i + 100]
            r = requests.post(
                f"{API}/crm/v3/objects/contacts/batch/read",
                headers=_headers(token),
                json={"properties": ["firstname", "lastname", "email"],
                      "inputs": [{"id": c} for c in lote]}, timeout=TIMEOUT)
            if r.status_code != 200:
                continue
            for c in r.json().get("results", []):
                p = c.get("properties", {})
                nombre = f"{p.get('firstname','') or ''} {p.get('lastname','') or ''}".strip()
                email = p.get("email", "") or ""
                etiqueta = nombre or "Sin nombre"
                if email:
                    etiqueta = f"{etiqueta} ({email})"
                contacto_info[c["id"]] = etiqueta
    except requests.exceptions.RequestException:
        pass
    # 3) unir
    return {tid: contacto_info.get(cid, "") for tid, cid in ticket_contacto.items()}


# ----------------------------------------------------------------------
# ORQUESTADOR: API -> DataFrame canónico (nombres de display)
# ----------------------------------------------------------------------
def cargar_desde_hubspot(token: str, pipeline: str = PIPELINE_INCIDENCIAS) -> pd.DataFrame:
    """
    Trae los tickets en vivo y devuelve un DataFrame con nombres de columna
    de display (los que reconoce data_loader.enriquecer_tickets).
    Incluye columnas numéricas de tiempo real (ms_*) que el archivo no tiene.
    """
    crudos = _buscar_tickets(token, pipeline)
    if not crudos:
        raise ValueError("HubSpot no devolvió tickets para ese pipeline. "
                         "Verifica el ID de pipeline y los permisos del token.")

    etapas = _etapas_pipeline(token, pipeline)
    owners = _propietarios(token)
    ids = [t["id"] for t in crudos]
    contactos = _contactos_de_tickets(token, ids)

    filas = []
    for t in crudos:
        p = t.get("properties", {})
        tid = t["id"]
        filas.append({
            "Ticket ID": tid,
            "Nombre del ticket": p.get("subject"),
            "Associated Contact": contactos.get(tid, ""),
            "Descripción del ticket": p.get("content"),
            "Prioridad": p.get("hs_ticket_priority"),
            "Estado del ticket": etapas.get(p.get("hs_pipeline_stage"),
                                            p.get("hs_pipeline_stage")),
            "Fecha de cierre": p.get("closed_date"),
            "Fecha de creación": p.get("createdate"),
            "Resolución": p.get("hs_resolution"),
            "Categoría": p.get("hs_ticket_category"),
            "Propietario del ticket": owners.get(p.get("hubspot_owner_id"), ""),
            "Fuente": p.get("source_type"),
            # columnas numéricas de tiempo REAL (ms) — exclusivas de la API
            "ms_cierre": p.get("hs_time_to_close"),
            "ms_primera_resp": p.get("hs_time_to_first_response"),
        })
    return pd.DataFrame(filas)
