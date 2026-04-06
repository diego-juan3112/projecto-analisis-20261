"""
Punto de entrada de demostración: mismo flujo que GeoMIP Method2 para un caso fijo.
Ajusta cadenas de bits o usa variables de entorno para TPM de muestra.
"""

import os
from pathlib import Path

import numpy as np

from src.controllers.manager import Manager
from src.models.base.application import aplicacion

from hfskmip.subcube_factor import SubcubeFactorSIA


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_tpm_path(estado_inicial: str) -> Path:
    name = f"N{len(estado_inicial)}A.csv"
    repo = _repo_root()
    for candidate in (
        repo / "GeoMIP" / "data" / "samples" / name,
        repo / "QNodes" / "src" / ".samples" / name,
    ):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No se encontró la TPM de muestra '{name}'. Colócala en GeoMIP/data/samples/ o QNodes/src/.samples/."
    )


def iniciar() -> None:
    aplicacion.profiler_habilitado = False

    estado_inicial = os.getenv("HFS_ESTADO_INICIAL", "1000")
    condiciones = os.getenv("HFS_CONDICIONES", "1111")
    alcance = os.getenv("HFS_ALCANCE", "1111")
    mecanismo = os.getenv("HFS_MECANISMO", "1111")

    tpm_path = Path(os.getenv("HFS_TPM_PATH", str(_default_tpm_path(estado_inicial))))
    tpm = np.genfromtxt(tpm_path, delimiter=",")

    subcube_dim = os.getenv("HFS_SUBCUBE_DIM")
    k = int(subcube_dim) if subcube_dim else None
    max_sc = int(os.getenv("HFS_MAX_SUBCUBES", "64"))
    top_k = int(os.getenv("HFS_TOP_K", "5"))
    decomp = os.getenv("HFS_DECOMPOSITION", "index_partition").strip().lower()
    if decomp not in ("index_partition", "sample_faces"):
        decomp = "index_partition"

    gestor = Manager(estado_inicial=estado_inicial)
    sia = SubcubeFactorSIA(
        gestor,
        subcube_dim=k,
        max_subcubes=max_sc,
        top_k_candidates=top_k,
        decomposition_mode=decomp,
    )
    sol = sia.aplicar_estrategia(condiciones, alcance, mecanismo, tpm)
    sol.hablar = False  # evita bloqueos de pyttsx3 en algunos entornos Windows
    print(sol)


if __name__ == "__main__":
    iniciar()
