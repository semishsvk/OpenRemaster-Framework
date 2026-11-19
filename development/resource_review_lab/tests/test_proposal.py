"""Offline contract shape tests; never import K003 or D7."""
import copy,json,unittest
from pathlib import Path
from jsonschema import Draft202012Validator

class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.schema=json.loads((Path(__file__).parent.parent/'schemas/named-dev-build-proposal.schema.json').read_text())
        self.validator=Draft202012Validator(self.schema)
        self.good={k: v.get('const','a'*64) for k,v in self.schema['properties'].items()}
        self.good.update(operation_id='a'*32,timeout_seconds=2400)
    def test_proposal_shape_only(self):
        Draft202012Validator.check_schema(self.schema)
        self.validator.validate(self.good)
    def test_each_required_binding(self):
        for key in self.good:
            with self.subTest(key=key):
                value=copy.deepcopy(self.good);del value[key]
                self.assertTrue(list(self.validator.iter_errors(value)))
    def test_negative_inputs(self):
        cases={'trust_class':'SECURE_PRODUCTION','action':'status','kind':'executable_runtime','project':'OpenAzrael','recipe':'arbitrary','adapter':'RemoteDesktopCommander','operation_id':'../x','source_manifest_sha256':'A'*64,'owner_fence_sha256':'','resource_fence_sha256':None,'timeout_seconds':2401,'automatic_retries':1,'capability':'process.exec'}
        for key,value in cases.items():
            with self.subTest(key=key):
                candidate=dict(self.good);candidate[key]=value
                self.assertTrue(list(self.validator.iter_errors(candidate)))
    def test_no_unrestricted_fields(self):
        for key in ('executable','args','cwd','shell','credentials','fallback','may_sign','production_go'):
            with self.subTest(key=key):
                candidate=dict(self.good);candidate[key]='forbidden'
                self.assertTrue(list(self.validator.iter_errors(candidate)))
    def test_bounds(self):
        for value in (0,-1,2401,1.5,'2400',True):
            with self.subTest(value=value):
                candidate=dict(self.good,timeout_seconds=value)
                self.assertTrue(list(self.validator.iter_errors(candidate)))
if __name__=='__main__':unittest.main()
