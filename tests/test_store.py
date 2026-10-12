import time

from automati.logic.smart_home.store import TimerStore


def test_un_timer_sobrevive_al_reinicio_del_proceso(tmp_path):
    path = str(tmp_path / "timers.db")
    store = TimerStore(path)
    timer = store.add(item="fan", seconds=1800)
    store.close()

    revivido = TimerStore(path)
    pendientes = revivido.pending()

    assert [t.id for t in pendientes] == [timer.id]
    assert pendientes[0].item == "fan"


def test_due_solo_devuelve_los_vencidos(tmp_path):
    store = TimerStore(str(tmp_path / "timers.db"))
    vencido = store.add(item="light", seconds=10)
    store.add(item="fan", seconds=9999)

    assert [t.id for t in store.due(now=time.time() + 60)] == [vencido.id]


def test_pending_ordena_por_proximidad(tmp_path):
    store = TimerStore(str(tmp_path / "timers.db"))
    lejano = store.add(item="fan", seconds=900)
    cercano = store.add(item="light", seconds=60)

    assert [t.id for t in store.pending()] == [cercano.id, lejano.id]


def test_mark_saca_al_timer_de_pendientes(tmp_path):
    store = TimerStore(str(tmp_path / "timers.db"))
    timer = store.add(item="fan", seconds=600)

    store.mark(timer.id, "done")

    assert store.pending() == []
