
import asyncio
import os
import signal
import sys
from typing import List, Set

class PipelineManager:
    def __init__(self):
        self._process = None
        self._clients: Set = set()
        self.current_stage = "Idle"
        self.orchestrator_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "auto_case_scrape_convert_ingest_digest",
            "run_pipeline.py"
        )
        self.cwd = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    def is_running(self):
        return self._process is not None and self._process.returncode is None

    def register_client(self, websocket):
        self._clients.add(websocket)

    def unregister_client(self, websocket):
        self._clients.discard(websocket)

    async def broadcast_log(self, message: str):
        if not self._clients: return
        for client in list(self._clients):
            try:
                await client.send_text(message)
            except:
                self._clients.discard(client)

    async def start_pipeline(self, targets: List[str] = None, mode: str = "auto", skip_scrape: bool = False, skip_convert: bool = False):
        """Async start using asyncio.create_subprocess_exec"""
        if self.is_running(): return

        # 1. Update Target List
        if targets:
            try:
                target_file_path = os.path.join(
                    self.cwd, "auto_case_scrape_convert_ingest_digest", "target_list.txt"
                )
                with open(target_file_path, "w") as f:
                    for t in targets:
                        f.write(t + "\n")
                await self.broadcast_log(f"📝 Updated targets: {len(targets)} cases.")
            except Exception as e:
                await self.broadcast_log(f"⚠️ Error updating targets: {e}")

        self.current_stage = "Starting"
        await self.broadcast_log(f"🚀 Pipeline Started (Mode: {mode.upper()})...")

        cmd = [sys.executable, "-u", self.orchestrator_path]
        cmd.extend(["--mode", mode])
        if skip_scrape:
            cmd.append("--skip-scrape")
        if skip_convert:
            cmd.append("--skip-convert")

        try:
            # 2. Spawn Async Subprocess
            # Use sys.executable to ensure we use the same python env
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.cwd
            )

            self.current_stage = "Running"

            # 3. Read Output Stream Line by Line
            while True:
                line = await self._process.stdout.readline()
                if not line: break
                
                decoded_line = line.decode('utf-8', errors='replace').strip()
                if decoded_line:
                    await self.broadcast_log(decoded_line)

            # 4. Cleanup
            return_code = await self._process.wait()
            self._process = None
            
            if return_code == 0:
                await self.broadcast_log("✅ Pipeline Completed Successfully.")
                self.current_stage = "Completed"
            else:
                await self.broadcast_log(f"❌ Pipeline Failed with code {return_code}.")
                self.current_stage = "Failed"

        except Exception as e:
            await self.broadcast_log(f"🔥 Critical Error: {e}")
            self.current_stage = "Error"
            self._process = None

    def stop_pipeline(self):
        if self._process:
            self.current_stage = "Stopping"
            try:
                self._process.terminate()
            except Exception:
                pass
            # We don't wait here, the async loop will handle the exit
