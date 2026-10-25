"""Synthetic typed-state regressions; not an original-game save roundtrip."""
import copy
import unittest
from glca.core import Hold,state_roundtrip
from glca.retail import FIELDS,typed_state

def save_state(value):
    state={key:{} for key in ('actors','inventory','timers','scripts','rooms','globals','camera')}
    state['globals']={'flag':value};return state

def fields(value):
    result={key:{'known':True,'value':{}} for key in FIELDS}
    result['globals']['value']=value;return result

class StateIdentityTests(unittest.TestCase):
    def test_save_comparison_preserves_boolean_integer_distinction(self):
        self.assertEqual(state_roundtrip(save_state(False),save_state(0))['differences'],['globals'])
    def test_save_comparison_preserves_integer_float_distinction(self):
        self.assertEqual(state_roundtrip(save_state(1),save_state(1.0))['differences'],['globals'])
    def test_nested_unknown_not_a_complete_known_state(self):
        with self.assertRaises(Hold):typed_state('fixture',fields({'won':None}))
    def test_save_comparison_rejects_nested_unknown(self):
        with self.assertRaises(Hold):state_roundtrip(save_state(None),save_state(None))
    def test_nonstring_keys_are_not_silently_coerced(self):
        with self.assertRaises(Hold):typed_state('fixture',fields({1:'value'}))
    def test_python_tuples_are_not_silently_coerced(self):
        with self.assertRaises(Hold):typed_state('fixture',fields((1,2)))
    def test_state_depth_is_bounded(self):
        value=True
        for _ in range(40):value={'nested':value}
        with self.assertRaises(Hold):typed_state('fixture',fields(value))
    def test_state_element_count_is_bounded(self):
        with self.assertRaises(Hold):typed_state('fixture',fields([0]*10001))
    def test_key_order_does_not_change_identity(self):
        a=typed_state('fixture',fields({'a':1,'b':False}))
        b=typed_state('fixture',fields({'b':False,'a':1}))
        self.assertEqual(a['state_digest'],b['state_digest'])
    def test_array_order_stays_observable(self):
        self.assertNotEqual(typed_state('fixture',fields([1,2]))['state_digest'],typed_state('fixture',fields([2,1]))['state_digest'])
    def test_false_and_zero_have_distinct_state_digests(self):
        self.assertNotEqual(typed_state('fixture',fields(False))['state_digest'],typed_state('fixture',fields(0))['state_digest'])
    def test_repeated_container_alias_is_detached_not_a_cycle(self):
        value={'flag':True};data=fields([value,value]);before=copy.deepcopy(data)
        result=typed_state('fixture',data);value['flag']=False
        self.assertEqual(result['fields']['globals']['value'],[{'flag':True},{'flag':True}])
        self.assertNotEqual(data,before)
    def test_cyclic_input_rejected_as_hold(self):
        value=[];value.append(value)
        with self.assertRaises(Hold):typed_state('fixture',fields(value))
    def test_nonfinite_input_rejected_as_hold(self):
        for value in (float('nan'),float('inf'),float('-inf')):
            with self.subTest(value=value):
                with self.assertRaises(Hold):typed_state('fixture',fields(value))
    def test_unknown_field_remains_explicit_and_incomplete(self):
        data=fields({});data['terminal']={'known':False}
        result=typed_state('fixture',data)
        self.assertFalse(result['complete']);self.assertEqual(result['fields']['terminal'],{'known':False})
    def test_successful_fixture_comparison_never_claims_native_roundtrip(self):
        result=state_roundtrip(save_state({'flag':[True,1,1.0]}),save_state({'flag':[True,1,1.0]}))
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['native_roundtrip_verified'])

if __name__=='__main__':unittest.main(verbosity=2)
