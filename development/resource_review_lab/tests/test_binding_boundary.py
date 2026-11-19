import unittest
import test_binding as fixture

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.BindingTests(methodName='test_bound_is_still_hold');self.f.setUp()
    def test_malformed_identity_inputs(self):
        for value in (None,[],{},True,{'request':{}}):
            with self.subTest(value=value):
                self.f.r.inputs=value
                self.assertFalse(self.f.call()['binding_checks_satisfied'])
    def test_malformed_proposals(self):
        for value in (None,[],True,{'schema':'wrong'}):
            with self.subTest(value=value):
                self.f.proposal=value
                self.assertFalse(self.f.call()['binding_checks_satisfied'])
    def test_cross_project_is_not_implicitly_mapped(self):
        self.f.proposal['project']='SYNTHETIC'
        self.assertEqual(self.f.call()['reason'],'PROPOSAL_SCHEMA')
    def test_trust_escalation_rejected(self):
        self.f.proposal['trust_class']='SECURE_PRODUCTION'
        self.assertFalse(self.f.call()['binding_checks_satisfied'])
    def test_self_attested_recipe_is_not_added(self):
        self.f.proposal['verified_recipe']=True
        self.assertEqual(self.f.call()['reason'],'PROPOSAL_SCHEMA')
    def test_missing_current_resource_context(self):
        self.f.r.expected=None
        self.assertFalse(self.f.call()['binding_checks_satisfied'])
    def test_foreign_resource_fence(self):
        self.f.r.obs['resource_fence']+=1
        self.assertFalse(self.f.call()['binding_checks_satisfied'])
    def test_nonfinite_and_boolean_pins(self):
        for value in (float('nan'),True,{},[]):
            with self.subTest(value=value):
                self.f.pins['recipe_sha256']=value
                self.assertEqual(self.f.call()['reason'],'RECIPE_PINS_INVALID')
