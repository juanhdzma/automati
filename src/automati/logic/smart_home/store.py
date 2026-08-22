"""Persistencia de los apagados diferidos, en SQLite.

# Que guarda

Un solo tipo de fila: "apagar `item` en el momento `run_at`". El servicio prende
el device al toque, en el mismo request, y guarda aca solo la parte que hay que
recordar despues: el apagado.

# Por que se persiste

La imagen se redeploya seguido desde Portainer con `:latest`, asi que el container
se recrea a menudo. Sin esto, un timer en memoria se perderia en cada redeploy y
el ventilador se quedaria prendido indefinidamente — sin un solo error en ningun
log. Ese modo de fallar en silencio es el que hay que evitar.

Al arrancar, el servicio relee los pendientes de esta tabla y sigue donde quedo.

# Por que no hace falta poder cancelar ni listar por HTTP

Apagar es idempotente: si alguien apago el device a mano antes de que venza el
timer, cuando venza el `turn_off` no cambia nada. No hay estado que "romper" por
dejar un timer vivo, asi que no hace falta poder cancelarlo desde afuera.

# Por que SQLite y no algo mas

Son unas pocas filas y un solo proceso escribiendo. `sqlite3` viene en la stdlib
y no agrega dependencias. Postgres o Redis para esto serian una VM entera para
guardar un puñado de apagados pendientes.
"""

import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS timers (
    id         TEXT PRIMARY KEY,
    item       TEXT NOT NULL,
    run_at     REAL NOT NULL,
    created_at REAL NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending',
    detail     TEXT
);
CREATE INDEX IF NOT EXISTS idx_timers_pending ON timers (status, run_at);
"""


@dataclass(frozen=True)
class Timer:
    id: str
    item: str
    run_at: float
    created_at: float
    status: str
    detail: str | None = None


class TimerStore:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def add(self, item: str, seconds: float) -> Timer:
        now = time.time()
        timer = Timer(
            id=uuid.uuid4().hex[:12],
            item=item,
            run_at=now + seconds,
            created_at=now,
            status="pending",
        )
        self._db.execute(
            "INSERT INTO timers (id, item, run_at, created_at, status)"
            " VALUES (?, ?, ?, ?, ?)",
            (timer.id, timer.item, timer.run_at, timer.created_at, timer.status),
        )
        self._db.commit()
        return timer

    def pending(self) -> list[Timer]:
        rows = self._db.execute(
            "SELECT * FROM timers WHERE status = 'pending' ORDER BY run_at"
        ).fetchall()
        return [Timer(**dict(r)) for r in rows]

    def due(self, now: float | None = None) -> list[Timer]:
        rows = self._db.execute(
            "SELECT * FROM timers WHERE status = 'pending' AND run_at <= ? ORDER BY run_at",
            (now if now is not None else time.time(),),
        ).fetchall()
        return [Timer(**dict(r)) for r in rows]

    def mark(self, timer_id: str, status: str, detail: str | None = None) -> None:
        self._db.execute(
            "UPDATE timers SET status = ?, detail = ? WHERE id = ?",
            (status, detail, timer_id),
        )
        self._db.commit()
