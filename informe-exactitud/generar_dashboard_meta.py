"""
Genera dashboard_exactitud.html a partir de "Exactitud_Meta_Mensual.xlsx".

Este archivo reemplaza al metodo anterior (CSV por semana desde tablas
dinamicas). Es una tabla plana, una fila por SKU x Mes x Tipo Indicador:

    Mes | CPFR | Cadena | SKU | Nombre | Categoria Producto |
    Tipo Indicador (MENSUAL/SEMANAL) | Meta | Venta SI | Error Abs | Exactitud

Notas importantes (verificadas con los datos, no asumidas):
- CPFR = Cadena + Tipo de Almacenamiento (ej. "WALMART FRIO", "TOTTUS SECO").
  Canal Tradicional y Supermercados Region no se dividen en Frio/Seco.
- "Tipo Indicador" MENSUAL vs SEMANAL NO son duplicados de la misma cadena:
  cada CPFR usa casi exclusivamente uno de los dos (ej. "ALVI FRIO" viene
  siempre como SEMANAL, "ALVI SECO" siempre como MENSUAL) - es solo la
  cadencia con la que esa cadena/categoria actualiza su meta. Para totales
  de mes hay que SUMAR ambos tipos, nunca filtrar por uno solo, o se
  pierden cadenas enteras.
- Este archivo NO trae detalle por semana individual dentro del mes -
  solo por mes. El ultimo mes disponible esta en curso (parcial).
- Formula de exactitud agregada (confirmada por el usuario, misma que la
  columna Exactitud por fila): Exact = max(0, 1 - sum(Error Abs)/sum(Meta)).
  Desv = (sum(Venta SI) - sum(Meta)) / sum(Meta).

Uso:
    python3 generar_dashboard_meta.py "Exactitud_Meta_Mensual.xlsx"
"""
import json
import sys
import warnings
from pathlib import Path
from collections import defaultdict

warnings.filterwarnings("ignore")
from openpyxl import load_workbook

HERE = Path(__file__).parent
OUT_HTML = HERE / "dashboard_exactitud.html"
META_OBJETIVO = 0.70  # ajustar aqui si cambia la meta corporativa


def leer_filas(path):
    wb = load_workbook(path, data_only=True, read_only=True, keep_links=False)
    ws = wb[wb.sheetnames[0]]
    filas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        mes = row[0]
        if not mes:
            continue
        filas.append({
            "mes": str(mes), "cpfr": row[1], "cadena": row[2], "sku": row[3],
            "nombre": row[4], "categoria": row[5], "tipo_ind": row[6],
            "meta": row[7] or 0, "si": row[8] or 0, "err": row[9] or 0,
            "exact_fila": row[10],
        })
    return filas


def agg(filas):
    meta = sum(f["meta"] for f in filas)
    si = sum(f["si"] for f in filas)
    err = sum(f["err"] for f in filas)
    # Exactitud = promedio simple de la columna "Exactitud" por fila, para
    # calzar con el PivotTable de referencia de la empresa (agregacion
    # "Promedio", no ponderada por volumen - verificado con el usuario).
    exacts = [f["exact_fila"] for f in filas if f["exact_fila"] is not None]
    exact = sum(exacts) / len(exacts) if exacts else None
    desv = (si - meta) / meta if meta else None
    return {"meta": round(meta, 1), "si": round(si, 1), "err": round(err, 1),
            "exact": round(exact, 4) if exact is not None else None,
            "desv": round(desv, 4) if desv is not None else None,
            "n_sku": len({f["sku"] for f in filas})}


def group_by(filas, key):
    out = defaultdict(list)
    for f in filas:
        out[f[key]].append(f)
    return out


def group_by_tuple(filas, key1, key2):
    out = defaultdict(list)
    for f in filas:
        out[(f[key1], f[key2])].append(f)
    return out


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    filas = leer_filas(sys.argv[1])  # MENSUAL + SEMANAL combinados = total real del mes

    meses = sorted({f["mes"] for f in filas})
    ultimo_mes = meses[-1]
    anio_actual = ultimo_mes[:4]
    meses_anio = [m for m in meses if m.startswith(anio_actual)]

    # A) Evolucion mensual del anio actual (total compania)
    evolucion = [{"mes": mes, **agg([f for f in filas if f["mes"] == mes])} for mes in meses_anio]

    # B) Cadena ranking del ultimo mes
    filas_ultimo_mes = [f for f in filas if f["mes"] == ultimo_mes]
    por_cadena = group_by(filas_ultimo_mes, "cadena")
    cadena_ranking = [{"cadena": c, **agg(fs)} for c, fs in por_cadena.items()]
    cadena_ranking.sort(key=lambda r: (r["exact"] if r["exact"] is not None else 1))

    # C) Matriz CPFR x mes (anio actual) + total anual por CPFR
    cpfrs = sorted({f["cpfr"] for f in filas if f["cpfr"]})
    filas_anio = [f for f in filas if f["mes"].startswith(anio_actual)]
    matriz_cpfr = {}
    total_anual_cpfr = {}
    for cpfr in cpfrs:
        fila = {}
        for mes in meses_anio:
            fs = [f for f in filas if f["mes"] == mes and f["cpfr"] == cpfr]
            fila[mes] = agg(fs) if fs else None
        matriz_cpfr[cpfr] = fila
        fs_anio = [f for f in filas_anio if f["cpfr"] == cpfr]
        total_anual_cpfr[cpfr] = agg(fs_anio) if fs_anio else None

    # D) Detalle por categoria: acumulado del anio + mes actual, filtrable por CPFR en el HTML
    def detalle_categoria(filas_base):
        por_cat = group_by(filas_base, "categoria")
        return sorted(
            [{"categoria": c, **agg(fs)} for c, fs in por_cat.items() if c],
            key=lambda r: (r["exact"] if r["exact"] is not None else 1)
        )

    detalle = {"TODAS": {"acumulado": detalle_categoria(filas_anio), "mes_actual": detalle_categoria(filas_ultimo_mes)}}
    for cpfr in cpfrs:
        detalle[cpfr] = {
            "acumulado": detalle_categoria([f for f in filas_anio if f["cpfr"] == cpfr]),
            "mes_actual": detalle_categoria([f for f in filas_ultimo_mes if f["cpfr"] == cpfr]),
        }

    # E) Top SKU mas desviados por cadena (mayor |desviacion|), acumulado y mes actual
    TOP_N_SKU = 15
    cadenas = sorted({f["cadena"] for f in filas if f["cadena"]})

    def top_sku_cadena(filas_base, cadena):
        por_sku = group_by([f for f in filas_base if f["cadena"] == cadena], "sku")
        filas_sku = []
        for sku, fs in por_sku.items():
            if not sku:
                continue
            a = agg(fs)
            filas_sku.append({
                "sku": sku, "nombre": fs[0]["nombre"], "categoria": fs[0]["categoria"], **a,
            })
        filas_sku.sort(key=lambda r: r["exact"] if r["exact"] is not None else 1)
        return filas_sku[:TOP_N_SKU]

    top_sku_por_cadena = {
        "acumulado": {c: top_sku_cadena(filas_anio, c) for c in cadenas},
        "mes_actual": {c: top_sku_cadena(filas_ultimo_mes, c) for c in cadenas},
    }

    # F) Control Tower: KPIs, heatmap Cadena x Categoria, alertas, cambios,
    #    impacto por cadena (toneladas) y top 5 SKU por impacto de volumen.
    idx_ultimo = meses_anio.index(ultimo_mes)
    mes_anterior = meses_anio[idx_ultimo - 1] if idx_ultimo > 0 else None
    filas_mes_anterior = [f for f in filas if f["mes"] == mes_anterior] if mes_anterior else []

    UMBRAL_CRITICO_SKU = 0.50

    def contar_sku_criticos(filas_base):
        por_sku = group_by(filas_base, "sku")
        return sum(1 for sku, fs in por_sku.items() if sku and (agg(fs)["exact"] or 0) < UMBRAL_CRITICO_SKU)

    total_mes_anterior = agg(filas_mes_anterior) if filas_mes_anterior else None
    sku_criticos_actual = contar_sku_criticos(filas_ultimo_mes)
    sku_criticos_anterior = contar_sku_criticos(filas_mes_anterior) if filas_mes_anterior else None

    kpis = {
        "exactitud_global": agg(filas_ultimo_mes)["exact"],
        "exactitud_global_anterior": total_mes_anterior["exact"] if total_mes_anterior else None,
        "gap_meta": (agg(filas_ultimo_mes)["exact"] or 0) - META_OBJETIVO,
        "sku_criticos": sku_criticos_actual,
        "sku_criticos_anterior": sku_criticos_anterior,
        "cadena_critica": cadena_ranking[0]["cadena"] if cadena_ranking else None,
        "cadena_critica_exact": cadena_ranking[0]["exact"] if cadena_ranking else None,
    }

    def heatmap_cadena_categoria(filas_base):
        matriz = {}
        for cadena, fs_cad in group_by(filas_base, "cadena").items():
            if not cadena:
                continue
            por_cat = group_by(fs_cad, "categoria")
            matriz[cadena] = {cat: agg(fs) for cat, fs in por_cat.items() if cat}
        return matriz

    heatmap = heatmap_cadena_categoria(filas_ultimo_mes)
    categorias_heatmap = sorted({cat for fila in heatmap.values() for cat in fila})

    # Alertas: combinaciones cadena+categoria con peor exactitud del mes,
    # con variacion vs mes anterior cuando existe.
    def cadena_categoria_exact(filas_base):
        out = {}
        for (cadena, cat), fs in group_by_tuple(filas_base, "cadena", "categoria").items():
            if cadena and cat:
                out[(cadena, cat)] = agg(fs)["exact"]
        return out

    actual_cc = cadena_categoria_exact(filas_ultimo_mes)
    anterior_cc = cadena_categoria_exact(filas_mes_anterior) if filas_mes_anterior else {}

    alertas = []
    for (cadena, cat), exact in actual_cc.items():
        if exact is None:
            continue
        var = (exact - anterior_cc[(cadena, cat)]) if (cadena, cat) in anterior_cc else None
        if exact < 0.40:
            estado = "CRITICO"
        elif exact < 0.55:
            estado = "ALERTA"
        else:
            continue
        alertas.append({"cadena": cadena, "categoria": cat, "exact": exact, "var": var, "estado": estado})
    alertas.sort(key=lambda a: a["exact"])
    alertas = alertas[:8]

    # Impacto por cadena: brecha de volumen (Meta - Venta SI) en toneladas.
    impacto_cadena = []
    for cadena, fs in group_by(filas_ultimo_mes, "cadena").items():
        if not cadena:
            continue
        a = agg(fs)
        impacto_cadena.append({"cadena": cadena, "brecha": round(a["meta"] - a["si"], 1)})
    impacto_cadena.sort(key=lambda r: r["brecha"], reverse=True)

    # Top 5 SKU por impacto de volumen (|Meta - Venta SI|), mes actual, toda la compania.
    por_sku_actual = group_by(filas_ultimo_mes, "sku")
    top5_sku = []
    for sku, fs in por_sku_actual.items():
        if not sku:
            continue
        a = agg(fs)
        top5_sku.append({
            "sku": sku, "nombre": fs[0]["nombre"], "categoria": fs[0]["categoria"],
            "impacto": round(a["meta"] - a["si"], 1), "exact": a["exact"],
        })
    top5_sku.sort(key=lambda r: abs(r["impacto"]), reverse=True)
    top5_sku = top5_sku[:5]

    control_tower = {
        "kpis": kpis,
        "heatmap": heatmap,
        "categorias_heatmap": categorias_heatmap,
        "cadenas_heatmap": sorted(heatmap.keys()),
        "alertas": alertas,
        "impacto_cadena": impacto_cadena,
        "top5_sku": top5_sku,
        "mes_anterior": mes_anterior,
    }

    data = {
        "generado_desde_mes": ultimo_mes,
        "meta_objetivo": META_OBJETIVO,
        "evolucion": evolucion,
        "cadena_ranking": cadena_ranking,
        "matriz_cpfr": matriz_cpfr,
        "total_anual_cpfr": total_anual_cpfr,
        "meses_matriz": meses_anio,
        "cpfrs": cpfrs,
        "detalle": detalle,
        "cadenas": cadenas,
        "top_sku_por_cadena": top_sku_por_cadena,
        "total_acumulado": agg(filas_anio),
        "total_mes_actual": agg(filas_ultimo_mes),
        "control_tower": control_tower,
    }

    (HERE / "exactitud_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    template = (HERE / "dashboard_exactitud_template.html").read_text(encoding="utf-8")
    html = template.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Dashboard generado: {OUT_HTML} ({OUT_HTML.stat().st_size/1024:.0f} KB)")
    print(f"Ultimo mes (en curso): {ultimo_mes} | Meses en evolucion: {len(meses_anio)} | CPFR: {len(cpfrs)}")


if __name__ == "__main__":
    main()
