"""Permanent-removal ownership and deferred Store-write regressions.

Default mode uses real files and strict storage/service boundaries. --with-ha
uses Home Assistant's actual Store, frontend URL manager and final-write event.
No physical or external service is called, and no live user files are touched.
"""
from __future__ import annotations

import ast
import asyncio
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
REAL_HA = "--with-ha" in sys.argv
sys.argv = [arg for arg in sys.argv if arg != "--with-ha"]
PACKAGE = "hem_074_removal"
package = ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package


class FileStore:
    """Strict file boundary with the delayed write semantics under test."""
    def __init__(self, hass, version, key):
        self.hass, self.key = hass, key
        self.path = str(Path(hass.config.config_dir) / ".storage" / key)
        self.pending = None
        self._write_lock = asyncio.Lock()
        self._read_only = False

    async def async_load(self):
        path = Path(self.path)
        return json.loads(path.read_text())["data"] if path.exists() else None

    async def async_save(self, value):
        async with self._write_lock:
            if not self._read_only:
                await self._async_write_data(value)

    async def _async_write_data(self, value):
        Path(self.path).parent.mkdir(exist_ok=True)
        Path(self.path).write_text(json.dumps({"key": self.key, "version": 1, "data": value}))

    def make_read_only(self):
        self._read_only = True

    def async_delay_save(self, snapshot, delay):
        async def write():
            await self.async_save(snapshot())
        self.pending = asyncio.get_running_loop().call_later(
            delay, lambda: asyncio.create_task(write()))

    async def async_remove(self):
        if self.pending is not None:
            self.pending.cancel()
        Path(self.path).unlink(missing_ok=True)


if REAL_HA:
    from homeassistant.core import CoreState, HomeAssistant
    from homeassistant.helpers.storage import Store
    from homeassistant.components import frontend
    from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
else:
    Store = FileStore
    homeassistant = ModuleType("homeassistant")
    helpers = ModuleType("homeassistant.helpers")
    storage = ModuleType("homeassistant.helpers.storage")
    storage.Store = Store
    components = ModuleType("homeassistant.components")
    frontend = ModuleType("homeassistant.components.frontend")
    frontend.add_extra_js_url = lambda hass, url: hass.urls.add(url)
    frontend.remove_extra_js_url = lambda hass, url: hass.urls.remove(url)
    for name, module in (("homeassistant", homeassistant), ("homeassistant.helpers", helpers),
                         ("homeassistant.helpers.storage", storage),
                         ("homeassistant.components", components),
                         ("homeassistant.components.frontend", frontend)):
        sys.modules[name] = module


cleanup = importlib.import_module(PACKAGE + ".entry_cleanup")
const = importlib.import_module(PACKAGE + ".const")
tree = ast.parse((SOURCE / "__init__.py").read_text())
entry_ns = {"__package__": PACKAGE, "__name__": PACKAGE + ".__init__",
            "DOMAIN": const.DOMAIN, "PLATFORMS": const.PLATFORMS}
hooks = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
hooks.extend(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
             and node.name in ("async_unload_entry", "async_remove_entry"))
exec(compile(ast.fix_missing_locations(ast.Module(body=hooks, type_ignores=[])),
             str(SOURCE / "__init__.py"), "exec"), entry_ns)


class RemovalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name) if REAL_HA else NS(
            data={}, config=NS(config_dir=self.directory.name), urls=set())
        if not REAL_HA:
            self.hass.async_add_executor_job = asyncio.to_thread
        if REAL_HA:
            self.hass.state = CoreState.running
            self.hass.data[frontend.DATA_EXTRA_MODULE_URL] = frontend.UrlManager(lambda *_: None, [])
        self.original_services = getattr(self.hass, "services", None)
        self.entries = []
        self.dismissed = []
        self.removed_services = []
        self.unloads = []
        async def unload(entry, platforms):
            self.unloads.append(entry.entry_id)
            return True
        self.hass.config_entries = NS(async_entries=lambda domain: tuple(self.entries),
                                      async_unload_platforms=unload)
        async def call(domain, service, data, **kwargs):
            self.assertEqual((domain, service), ("persistent_notification", "dismiss"))
            self.dismissed.append(data["notification_id"])
        self.hass.services = NS(has_service=lambda *_: True, async_call=call,
                                async_remove=lambda domain, service: self.removed_services.append((domain, service)))

    async def asyncTearDown(self):
        if REAL_HA:
            self.hass.services = self.original_services
            await self.hass.async_stop(force=True)
        self.directory.cleanup()

    def entry(self, identifier, areas=("room",)):
        entry = NS(entry_id=identifier, data={"areas": list(areas)}, options={})
        self.entries.append(entry)
        return entry

    async def seed(self, entry):
        stores = {key: Store(self.hass, 1, key) for key in cleanup.store_keys(entry.entry_id)}
        for store in stores.values():
            await store.async_save({"preserve": entry.entry_id})
        return stores

    def runtime(self, entry, stores, *, result=True, gate=None):
        manager = NS(_environment_store=stores[f"{const.DOMAIN}.environment_history_{entry.entry_id}"],
                     equipment=NS(records={}), faults=NS(_specs={}))
        manager._controllers = lambda: tuple((key, NS(_store=store)) for key, store in stores.items())
        async def stop():
            if gate:
                await gate.wait()
            return result
        manager.async_stop = stop
        entry.runtime_data = manager
        self.hass.data.setdefault(const.DOMAIN, {})[entry.entry_id] = manager
        return manager

    async def remove(self, entry):
        if entry in self.entries:
            self.entries.remove(entry)
        await entry_ns["async_remove_entry"](self.hass, entry)

    def exists(self, store):
        return Path(store.path).exists()

    async def test_unload_preserves_files_then_removal_targets_only_this_entry(self):
        first, second = self.entry("home"), self.entry("home_longer")
        own, other = await self.seed(first), await self.seed(second)
        recorder = Path(self.directory.name) / "home-assistant_v2.db"
        recorder.write_bytes(b"untouched-recorder")
        source = Path(self.directory.name) / ".storage" / "native_sensor.home"
        source.write_bytes(b"untouched-native")
        self.runtime(first, own)
        self.assertTrue(await entry_ns["async_unload_entry"](self.hass, first))
        self.assertTrue(all(self.exists(store) for store in own.values()))
        del first.runtime_data  # Home Assistant deletes this after successful unload.
        await self.remove(first)
        self.assertFalse(any(self.exists(store) for store in own.values()))
        self.assertTrue(all(self.exists(store) for store in other.values()))
        self.assertEqual(recorder.read_bytes(), b"untouched-recorder")
        self.assertEqual(source.read_bytes(), b"untouched-native")
        self.assertNotIn(cleanup.DATA_CLEANUP, self.hass.data)

    async def test_original_store_handle_cancels_a_delayed_write(self):
        entry = self.entry("delay")
        stores = await self.seed(entry)
        store = stores[f"{const.DOMAIN}.environment_history_delay"]
        store.async_delay_save(lambda: {"late": True}, 0.04)
        self.runtime(entry, stores)
        await entry_ns["async_unload_entry"](self.hass, entry)
        del entry.runtime_data
        await self.remove(entry)
        await asyncio.sleep(0.08)
        if REAL_HA:
            await self.hass.async_block_till_done()
        self.assertFalse(self.exists(store), "An old delayed writer recreated deleted storage")

    @unittest.skipUnless(REAL_HA, "Actual Home Assistant FINAL_WRITE lifecycle")
    async def test_original_store_handle_cancels_homeassistant_final_write(self):
        entry = self.entry("final_write")
        stores = await self.seed(entry)
        self.runtime(entry, stores)
        self.hass.state = CoreState.stopping
        store = stores[f"{const.DOMAIN}.pid_final_write"]
        await store.async_save({"deferred_until_final_write": True})
        await entry_ns["async_unload_entry"](self.hass, entry)
        del entry.runtime_data
        await self.remove(entry)
        self.hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
        await self.hass.async_block_till_done()
        self.assertFalse(self.exists(store))

    async def test_failed_stop_keeps_active_recovery_data_and_notices(self):
        entry = self.entry("failed")
        stores = await self.seed(entry)
        self.runtime(entry, stores, result=False)
        self.assertFalse(await entry_ns["async_unload_entry"](self.hass, entry))
        with self.assertRaisesRegex(RuntimeError, "writers did not stop"):
            await self.remove(entry)
        self.assertTrue(all(self.exists(store) for store in stores.values()))
        self.assertFalse(any(store._read_only for store in stores.values()))
        self.assertEqual(self.dismissed, [])

    async def test_inflight_store_write_finishes_before_unlink_and_cannot_recreate(self):
        entry = self.entry("inflight")
        stores = await self.seed(entry)
        store = stores[f"{const.DOMAIN}.environment_history_inflight"]
        self.runtime(entry, stores)
        entered, finish, revoked = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original = store._async_write_data
        original_read_only = store.make_read_only
        async def slow_write(data):
            entered.set()
            await finish.wait()
            await original(data)
        def make_read_only():
            original_read_only()
            revoked.set()
        with patch.object(store, "_async_write_data", slow_write), \
                patch.object(store, "make_read_only", make_read_only):
            writer = asyncio.create_task(store.async_save({"late_executor_result": True}))
            await entered.wait()
            removal = asyncio.create_task(self.remove(entry))
            try:
                await asyncio.wait_for(revoked.wait(), 1)
                self.assertFalse(removal.done())
                self.assertTrue(self.exists(store), "Deleted recovery data before its writer stopped")
            finally:
                finish.set()
            await writer
            await removal
        await store.async_save({"must_not_recreate": True})
        self.assertFalse(self.exists(store))

    async def test_removal_waits_for_running_writer_before_deletion(self):
        entry = self.entry("writing")
        stores = await self.seed(entry)
        gate = asyncio.Event()
        self.runtime(entry, stores, gate=gate)
        task = asyncio.create_task(self.remove(entry))
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        self.assertTrue(all(self.exists(store) for store in stores.values()))
        gate.set()
        await task
        self.assertFalse(any(self.exists(store) for store in stores.values()))
        self.assertNotIn(const.DOMAIN, self.hass.data)

    async def test_disabled_entry_removes_saved_ownership_not_other_entry_notices(self):
        entry = self.entry("disabled", ("room", "exclusive"))
        self.entry("survivor", ("room",))
        stores = await self.seed(entry)
        await stores[f"{const.DOMAIN}.equipment_disabled"].async_save({"records": {
            "old_controller": {"source_device_id": "physical", "area": "exclusive"}}})
        await self.remove(entry)
        own = cleanup._notice_ids("disabled", "old_controller", "physical")
        other = cleanup._notice_ids("survivor", "old_controller", "physical")
        self.assertTrue(own.issubset(self.dismissed))
        self.assertTrue(other.isdisjoint(self.dismissed))
        self.assertNotIn("environment_manager_room", self.dismissed)
        self.assertNotIn("environment_manager_shades_room_open", self.dismissed)
        self.assertIn("environment_manager_exclusive", self.dismissed)

    async def test_failure_removes_other_owned_files_and_keeps_retry_handles(self):
        entry = self.entry("io_error")
        stores = await self.seed(entry)
        self.runtime(entry, stores)
        failing = stores[f"{const.DOMAIN}.pid_io_error"]
        async def fail():
            raise OSError("test disk refusal")
        with patch.object(failing, "async_remove", fail), self.assertLogs(cleanup._LOGGER, "ERROR"):
            with self.assertRaisesRegex(RuntimeError, "1 HEM owned"):
                await self.remove(entry)
        self.assertTrue(self.exists(failing))
        self.assertEqual(sum(self.exists(store) for store in stores.values()), 1)
        await self.remove(entry)
        self.assertFalse(self.exists(failing))

    async def test_corrupt_journal_is_removed_without_creating_recovery_copies(self):
        entry = self.entry("corrupt")
        stores = await self.seed(entry)
        path = Path(stores[f"{const.DOMAIN}.equipment_corrupt"].path)
        path.write_text("{incomplete-json")
        with self.assertLogs(cleanup._LOGGER, "WARNING"):
            await self.remove(entry)
        self.assertFalse(path.exists())
        self.assertFalse(list(path.parent.glob(path.name + ".*")))

    async def test_frontend_url_removed_only_for_last_entry_and_restored_on_setup(self):
        first, last = self.entry("first"), self.entry("last")
        url = "/environment_manager/home-environment-manager-card.js?v=test"
        frontend.add_extra_js_url(self.hass, url)
        cleanup.remember_frontend_resource(self.hass, url)
        with patch.object(frontend, "remove_extra_js_url", wraps=frontend.remove_extra_js_url) as remove:
            await self.remove(first)
            remove.assert_not_called()
            await self.remove(last)
            remove.assert_called_once_with(self.hass, url)
        replacement = self.entry("replacement")
        with patch.object(frontend, "add_extra_js_url", wraps=frontend.add_extra_js_url) as add:
            cleanup.prepare_entry_setup(self.hass, replacement)
            cleanup.prepare_entry_setup(self.hass, replacement)
            add.assert_called_once_with(self.hass, url)

    async def test_reload_keeps_storage_and_releases_only_old_handles(self):
        entry = self.entry("reload")
        stores = await self.seed(entry)
        self.runtime(entry, stores)
        await entry_ns["async_unload_entry"](self.hass, entry)
        del entry.runtime_data
        cleanup.prepare_entry_setup(self.hass, entry)
        self.assertNotIn(cleanup.DATA_CLEANUP, self.hass.data)
        self.assertTrue(all(self.exists(store) for store in stores.values()))

    def test_inventory_covers_every_persistent_entry_store(self):
        observed = set()
        for path in SOURCE.glob("*.py"):
            if path.name == "entry_cleanup.py":
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "Store"):
                    continue
                self.assertGreaterEqual(len(node.args), 3, path.name)
                expression = node.args[2]
                self.assertIsInstance(expression, ast.JoinedStr, path.name)
                key = "".join(part.value if isinstance(part, ast.Constant)
                              else const.DOMAIN if isinstance(part.value, ast.Name)
                              and part.value.id == "DOMAIN" else "ENTRY"
                              for part in expression.values)
                observed.add(key)
        self.assertEqual(observed, set(cleanup.store_keys("ENTRY")))


if __name__ == "__main__":
    print("Removal test transport:", "Home Assistant Store" if REAL_HA else "strict local filesystem")
    unittest.main(verbosity=2)
