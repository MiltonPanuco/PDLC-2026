class EcoMarketClient:
    def __init__(self, url):
        self.url = url
        self.last_id = None
        self.activo = True
        self.retry_count = 0 # Para Backoff

    async def iniciar_monitoreo(self):
        while self.activo:
            headers = {"Accept": "text/event-stream"}
            if self.last_id: headers["Last-Event-ID"] = self.last_id

            try:
                # CORRECCIÓN A: Timeout=None para permitir silencio largo
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", self.url, headers=headers) as response:
                        self.retry_count = 0 
                        # CORRECCIÓN B & C: Buffer local por conexión
                        buffer_data = []
                        current_event = "message" 

                        async for line in response.aiter_lines():
                            if not line.strip():
                                if buffer_data:
                                    self._dispatch(current_event, "".join(buffer_data))
                                    buffer_data = []; current_event = "message" # RESET
                                continue
                            
                            if line.startswith("id:"): self.last_id = line[3:].strip()
                            elif line.startswith("event:"): current_event = line[6:].strip()
                            elif line.startswith("data:"): buffer_data.append(line[5:].strip())

            except Exception as e:
                # CORRECCIÓN D: Backoff Exponencial
                self.retry_count += 1
                wait = min(30, 2 ** self.retry_count)
                print(f"🔌 Error. Reintento en {wait}s...")
                await asyncio.sleep(wait)