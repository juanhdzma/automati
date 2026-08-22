"""Tests del timer: prender ya, apagar despues.

El caso que más importa es el de los timers vencidos hace mucho: después de un
corte de luz no se deben apagar tarde, porque no cumple ninguna intención y
probablemente ya se apagó a mano.
"""

import time

from automati.logic.smart_home import schedule
from automati.logic.smart_home.devices import DEVICES
from automati.logic.smart_home.store import TimerStore

from conftest import FakeClient


def _store(tmp_path):
    return TimerStore(str(tmp_path / "timers.db"))


async def test_start_timer_prende_ya_y_guarda_el_apagado(tmp_path):
    store, client = _store(tmp_path), FakeClient(["off"])

    result = await schedule.start_timer(client, store, "fan", seconds=1800)

    assert ("call_service", "switch", "turn_on", DEVICES["fan"].entity_id) in client.calls
    assert result.state == "on"
    assert len(store.pending()) == 1
    assert store.pending()[0].item == "fan"


async def test_run_due_apaga_un_timer_vencido(tmp_path):
    store, client = _store(tmp_path), FakeClient(["on"])
    store.add(item="fan", seconds=10)

    await schedule.run_due(client, store, now=time.time() + 30)

    assert ("call_service", "switch", "turn_off", DEVICES["fan"].entity_id) in client.calls
    assert store.pending() == []


async def test_no_toca_un_timer_que_todavia_no_vencio(tmp_path):
    store, client = _store(tmp_path), FakeClient(["on"])
    store.add(item="fan", seconds=9999)

    await schedule.run_due(client, store, now=time.time())

    assert client.calls == []
    assert len(store.pending()) == 1


async def test_descarta_los_vencidos_hace_demasiado(tmp_path):
    """Tras un corte de luz no se apagan los timers viejos tarde."""
    store, client = _store(tmp_path), FakeClient(["on"])
    store.add(item="fan", seconds=10)

    await schedule.run_due(
        client, store, now=time.time() + schedule.MAX_LATE_SECONDS + 60
    )

    assert client.calls == []
    assert store.pending() == []


async def test_un_vencido_reciente_si_se_apaga(tmp_path):
    """Un redeploy de treinta segundos no deberia perder un timer."""
    store, client = _store(tmp_path), FakeClient(["on"])
    store.add(item="fan", seconds=10)

    await schedule.run_due(client, store, now=time.time() + 40)

    assert ("call_service", "switch", "turn_off", DEVICES["fan"].entity_id) in client.calls


async def test_device_desconectado_al_vencer_no_frena_a_los_demas(tmp_path):
    store = _store(tmp_path)
    client = FakeClient(["unavailable"])
    store.add(item="fan", seconds=10)
    store.add(item="light", seconds=11)

    await schedule.run_due(client, store, now=time.time() + 30)

    assert store.pending() == []
