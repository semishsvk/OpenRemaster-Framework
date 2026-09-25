from hashlib import sha256
import pytest
from openremaster.archaeology import BinarySource, ByteRange, DecoderContract, DecodedRecord
from openremaster.binary_inventory import audit_ranges

def d(v):
    return sha256(v.encode()).hexdigest()

def test_range_is_bound_to_source_and_bounds():
    source = BinarySource("LEV4.MP1", d("source"), 100)
    ByteRange("LEV4.MP1", 10, 20, d("range")).validate(source)
    with pytest.raises(ValueError, match="outside"):
        ByteRange("LEV4.MP1", 90, 20, d("bad")).validate(source)

def test_decoder_contract_is_deterministic():
    a = DecoderContract("mp-decoder","1","cadaver-mp3",d("params"))
    assert a.digest() == a.digest()

def test_decoded_record_binds_range_decoder_and_output():
    source = BinarySource("LEV4.MP1", d("source"), 100)
    r = ByteRange("LEV4.MP1", 0, 16, d("range"))
    r.validate(source)
    DecodedRecord("rec-1",r,d("decoder"),d("output"),"TYPE2").validate()

def test_range_audit_detects_overlap_and_uncovered_bytes():
    source = BinarySource("x",d("x"),10)
    ranges = (
        ByteRange("x",0,6,d("a")),
        ByteRange("x",4,4,d("b")),
    )
    audit = audit_ranges(source,ranges)
    assert audit.covered_bytes == 8
    assert audit.overlap_bytes == 2
    assert audit.uncovered_bytes == 2
