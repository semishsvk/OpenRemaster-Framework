import hashlib
import unittest
from anchor import canonical, verify_current_anchor
from scope import Hold

STATE={"owner":"A","epoch":4}
OLD={"owner":"A","epoch":3}
ANCHOR={"sequence":4,"state_sha256":hashlib.sha256(canonical(STATE)).hexdigest()}
class AnchorTests(unittest.TestCase):
    def verify(self,state=STATE,anchor=ANCHOR,current=ANCHOR,signature=True):
        return verify_current_anchor(state,anchor,lambda:current,lambda _:signature)
    def test_current(self):
        self.assertTrue(self.verify())
    def test_old_state(self):
        with self.assertRaises(Hold): self.verify(state=OLD)
    def test_stale_anchor(self):
        with self.assertRaises(Hold): self.verify(anchor=dict(ANCHOR,sequence=3))
    def test_untrusted_signature(self):
        with self.assertRaises(Hold): self.verify(signature=False)
    def test_no_provider(self):
        with self.assertRaises(Hold): verify_current_anchor(STATE,ANCHOR,None,lambda _:True)
    def test_invalid_sequence(self):
        with self.assertRaises(Hold): self.verify(anchor=dict(ANCHOR,sequence=0),current=dict(ANCHOR,sequence=0))
if __name__=="__main__":
    unittest.main()
