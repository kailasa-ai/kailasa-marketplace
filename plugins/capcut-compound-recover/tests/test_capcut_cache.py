"""Behavioral tests with generated media; no private projects or fixture videos."""

import hashlib
import importlib.util
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "skills/capcut-compound-recover/scripts/capcut_cache.py"
spec = importlib.util.spec_from_file_location("capcut_cache", SCRIPT)
cache = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cache
spec.loader.exec_module(cache)


def trailer(step, length, key, cryptor_type=1):
    digest = cache.parameter_digest(step, length, key)
    child = struct.pack(">I4sII", 48, b"crpt", cryptor_type, 3) + digest
    return struct.pack(">I4s", 68, b"bdve") + child + struct.pack(">I4sI", 12, b"size", 68)


class FormatTests(unittest.TestCase):
    def test_novel_period_requires_exact_digest(self):
        step, length, key = 503, 307, 0x37
        positions = list(range(0, 25000, 107))
        observations = [(pos, pos % step < length) for pos in positions]
        self.assertEqual(cache.solve(observations, cache.parameter_digest(step, length, key),
                                     key, max_step=700), (step, length))
        with self.assertRaises(cache.RecoveryError):
            cache.solve(observations, b"\0" * 32, key, max_step=700)

    def test_periodic_restoration_preserves_plain_gaps_and_partial_last_block(self):
        original = random.Random(42).randbytes(10241)
        step, length, key = 503, 307, 0x37
        masked = bytes(value ^ key if offset % step < length else value
                       for offset, value in enumerate(original))
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "cache", Path(directory) / "restored"
            source.write_bytes(masked + trailer(step, length, key))
            cache.restore(source, output, len(masked), step, length, key)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(source.read_bytes(), masked + trailer(step, length, key))

    def test_footer_bounds_and_unsupported_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache"
            path.write_bytes(b"media" + trailer(503, 307, 0x37))
            parsed = cache.footer(path)
            self.assertEqual((parsed["start"], parsed["version"]), (5, 3))
            path.write_bytes(b"media" + trailer(503, 307, 0x37, cryptor_type=2))
            with self.assertRaises(cache.RecoveryError):
                cache.footer(path)
            path.write_bytes(b"media" + trailer(503, 307, 0x37)[:-20])
            self.assertIsNone(cache.footer(path))

    def test_project_locator_excludes_alpha_and_deduplicates_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "Example (1)"
            combo = project / "Resources/combination"
            combo.mkdir(parents=True)
            (project / "draft_meta_info.json").write_text(json.dumps({
                "draft_name": "Example (1)", "draft_id": "project-id", "tm_duration": 1000000
            }))
            (combo / "compound-id_video.mp4").touch()
            (combo / "compound-id_video.mp4.alpha.mp4").touch()
            found = cache.list_projects([root, root], "Example (1)")
            self.assertEqual(len(found), 1)
            self.assertEqual([c["combination_id"] for c in found[0]["caches"]], ["compound-id"])
            self.assertEqual(cache.list_projects([root], "Missing"), [])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.plain = cls.root / "generated.mp4"
        subprocess.run([
            "ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=size=96x160:rate=10", "-f", "lavfi", "-i",
            "sine=frequency=440:sample_rate=44100", "-t", "0.6", "-c:v", "libx264",
            "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.plain)
        ], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_plain_remux_and_verified_copy_preserve_source_and_packets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = self.plain.read_bytes()
            output = root / "result.mp4"
            report = cache.recover(self.plain, output, copy_to=root / "downloads")
            self.assertEqual(output.read_bytes(), (root / "downloads/result.mp4").read_bytes())
            self.assertEqual(self.plain.read_bytes(), before)
            self.assertEqual(report["audio_streams"], 1)
            self.assertEqual((report["width"], report["height"]), (96, 160))
            self.assertEqual(self.packet_hashes(self.plain), self.packet_hashes(output))

    @staticmethod
    def packet_hashes(path):
        result = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_packets", "-show_data_hash", "sha256",
            "-show_entries", "packet=stream_index,data_hash", "-of", "json", str(path)
        ], text=True)
        return sorted((p["stream_index"], p["data_hash"]) for p in json.loads(result)["packets"])

    def test_bdve_end_to_end_keeps_video_and_audio_packets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "compound_video.mp4"
            original = self.plain.read_bytes()
            step, length = cache.KNOWN_PROFILES[0]
            key = 0x3B
            masked = bytes(value ^ key if offset % step < length else value
                           for offset, value in enumerate(original))
            source.write_bytes(masked + trailer(step, length, key))
            expected_source = source.read_bytes()
            output = root / "recovered.mp4"
            report = cache.recover(source, output)
            self.assertTrue(report["bdve"]["digest_verified"])
            self.assertEqual(source.read_bytes(), expected_source)
            self.assertEqual(self.packet_hashes(self.plain), self.packet_hashes(output))

    def test_existing_destination_is_preserved_and_explicit_replacement_works(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.mp4"
            output.write_bytes(b"keep this unrelated file")
            with self.assertRaises(cache.RecoveryError):
                cache.recover(self.plain, output)
            self.assertEqual(output.read_bytes(), b"keep this unrelated file")
            cache.recover(self.plain, output, overwrite=True)
            self.assertEqual(self.packet_hashes(self.plain), self.packet_hashes(output))

    def test_failed_recovery_publishes_nothing_and_cannot_copy_over_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "bad_video.mp4"
            bad.write_bytes(b"incomplete cache")
            output = root / "result.mp4"
            with self.assertRaises(cache.RecoveryError):
                cache.recover(bad, output)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".capcut-recover-*")), [])
            with self.assertRaises(cache.RecoveryError):
                cache.recover(self.plain, root / self.plain.name,
                              copy_to=self.plain.parent, overwrite=True)
            alpha = root / "clip_video.mp4.alpha.mp4"
            alpha.write_bytes(self.plain.read_bytes())
            with self.assertRaisesRegex(cache.RecoveryError, "alpha mask"):
                cache.recover(alpha, output)


if __name__ == "__main__":
    unittest.main()
