from openremaster.failure import FailureDescriptor

def test_failure_id_is_sha_bound_and_deterministic():
    a = FailureDescriptor("openazrael", "sha", "collision", "room-1", "floor fall-through", "bundle")
    b = FailureDescriptor("openazrael", "sha", "collision", "room-1", "floor fall-through", "bundle")
    assert a.failure_id() == b.failure_id()
