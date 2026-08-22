class FakeClient:
    """Doble del HomeAssistantClient que registra la secuencia de llamadas.

    `states` es la cola de estados que devuelve `get_state`; el ultimo se repite.
    `calls` guarda la secuencia real de operaciones, que es lo que se assertea:
    que se lea el estado antes de actuar, y que a un device desconectado no se le
    mande nada.
    """

    def __init__(self, states: list[str | None]):
        self._states = list(states)
        self.calls: list[tuple] = []

    async def get_state(self, entity_id: str) -> dict:
        state = self._states.pop(0) if len(self._states) > 1 else self._states[0]
        self.calls.append(("get_state", entity_id))
        return {"state": state}

    async def call_service(self, domain: str, service: str, data: dict):
        self.calls.append(("call_service", domain, service, data["entity_id"]))
        return []
