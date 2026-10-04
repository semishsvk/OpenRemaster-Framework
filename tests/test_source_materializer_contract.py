from pathlib import Path

CONTRACT = Path("docs/contracts/source-materializer-v1.md")

REQUIRED = [
    "SourceMaterializeRequest.v1",
    "SourceAttestation.v1",
    "expected_sha256",
    "quarantine",
    "atomically",
    "read-only",
    "CyberMage commissioning canary",
    "CM_HI.EXE",
    "SCENE.RSC",
    "FXO.RSC",
    "PANEL00.DAT",
    "ANMH.RSC",
    "HIPAK.RSC",
]

FORBIDDEN_PERSISTENCE = [
    "MUST NOT:",
    "presigned URLs",
    "shell history",
    "durable logs",
]


def test_source_materializer_contract_exists_and_is_fail_closed():
    text = CONTRACT.read_text(encoding="utf-8")
    for marker in REQUIRED + FORBIDDEN_PERSISTENCE:
        assert marker in text, marker
    assert "delete quarantine file" in text
    assert "wrong expected digest fails closed" in text


def test_cybermage_canary_has_six_sha256_digests():
    text = CONTRACT.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.startswith("- ") and " — " in line]
    canary = [line for line in lines if any(name in line for name in REQUIRED[-6:])]
    assert len(canary) == 6
    for line in canary:
        digest = line.rsplit(" — ", 1)[1].strip()
        assert len(digest) == 64
        int(digest, 16)
