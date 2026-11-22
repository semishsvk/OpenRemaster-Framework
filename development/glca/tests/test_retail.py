import copy
import tempfile
from pathlib import Path
import unittest
from glca.core import Hold
from glca.retail import FIELDS,corpus_manifest,typed_state,validate_ir,solve_model,atlas

class RetailTests(unittest.TestCase):
    def fixture(self):
        corpus={'schema':'OpenRemaster.RLR.CorpusManifest.v1','project':'SYNTHETIC',
                'files':[dict(path='fixture.dat',bytes=16,sha256='a'*64)]}
        ref=dict(path='fixture.dat',sha256='a'*64,offset=0,length=4)
        ir=dict(schema='OpenRemaster.RLR.LogicIR.v1',project='SYNTHETIC',
                rooms=[dict(id='room',evidence_state='SOURCE_ONLY',source_refs=[ref])],
                objects=[],dialogues=[],puzzles=[],endings=[])
        return corpus,ir
    def test_deterministic_corpus_hashing_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.dat';p.write_bytes(b'original synthetic bytes')
            before=p.read_bytes();a=corpus_manifest(d,project='SYNTHETIC');b=corpus_manifest(d,project='SYNTHETIC')
            self.assertEqual(a,b);self.assertEqual(p.read_bytes(),before)
            self.assertEqual(a['files'][0]['format'],'UNKNOWN')
    def test_corpus_byte_and_file_limits(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'a').write_bytes(b'1234');(Path(d)/'b').write_bytes(b'1')
            for kwargs in [dict(max_bytes=2),dict(max_files=1)]:
                with self.assertRaises(Hold):corpus_manifest(d,project='SYNTHETIC',**kwargs)
    def test_state_unknown_never_false(self):
        fields={k:{'known':False} for k in FIELDS}
        unknown=typed_state('SYNTHETIC',fields)
        fields['terminal']={'known':True,'value':False}
        false=typed_state('SYNTHETIC',fields)
        self.assertNotEqual(unknown['state_digest'],false['state_digest'])
        self.assertFalse(false['complete'])
    def test_future_observable_state_distinctions(self):
        fields={k:{'known':True,'value':{}} for k in FIELDS}
        before=typed_state('SYNTHETIC',fields)
        for key in ('inventory','timers','npcs','save'):
            other=copy.deepcopy(fields);other[key]['value']={'changed':1}
            self.assertNotEqual(before['state_digest'],typed_state('SYNTHETIC',other)['state_digest'])
        self.assertNotEqual(before['state_digest'],typed_state('FOREIGN',fields)['state_digest'])
    def test_typed_state_rejects_implicit_unknown(self):
        fields={k:{'known':False} for k in FIELDS};fields['terminal']={'known':False,'value':False}
        with self.assertRaises(Hold):typed_state('SYNTHETIC',fields)
    def test_source_bound_world_dialogue_and_links(self):
        corpus,ir=self.fixture();row=copy.deepcopy(ir['rooms'][0]);row['id']='dialogue'
        row['links']=[dict(kind='rooms',id='room')];ir['dialogues'].append(row)
        self.assertEqual(validate_ir('SYNTHETIC',ir,corpus)['records'],2)
    def test_ir_negatives(self):
        for mutation in ('hash','offset','project','promotion','link','duplicate'):
            with self.subTest(mutation=mutation):
                corpus,ir=self.fixture();row=ir['rooms'][0]
                if mutation=='hash':row['source_refs'][0]['sha256']='b'*64
                if mutation=='offset':row['source_refs'][0]['offset']=20
                if mutation=='project':ir['project']='FOREIGN'
                if mutation=='promotion':row['evidence_state']='INDEPENDENT_ACCEPTED'
                if mutation=='link':row['links']=[dict(kind='objects',id='missing')]
                if mutation=='duplicate':ir['rooms'].append(copy.deepcopy(row))
                with self.assertRaises(Hold):validate_ir('SYNTHETIC',ir,corpus)
    def test_unknown_guards_cannot_create_completion_witness(self):
        result=solve_model(['s','win'],[dict(**{'from':'s','to':'win'},guard=None)],'s',['win'])
        self.assertEqual(result['path_witnesses'],{});self.assertEqual(result['status'],'HOLD')
    def test_witness_and_trap_are_model_only(self):
        result=solve_model(['s','win','trap'],[dict(**{'from':'s','to':'win'},guard=True),
                    dict(**{'from':'s','to':'trap'},guard=True)],'s',['win'],complete=True)
        self.assertEqual(result['path_witnesses']['win'],[dict(before='s',after='win')])
        self.assertEqual(result['confirmed_softlocks'],0)
        self.assertIn('trap',result['dead_end_candidates'])
    def test_atlas_preserves_unknown_runtime_coverage(self):
        corpus,ir=self.fixture();result=atlas('SYNTHETIC',ir,corpus,solve_model(['s'],[],'s',[]))
        self.assertEqual(result['coverage']['runtime'],'UNKNOWN');self.assertFalse(result['may_release'])
    def test_state_input_detached(self):
        fields={k:{'known':False} for k in FIELDS};result=typed_state('SYNTHETIC',fields)
        fields['terminal']['known']=True;self.assertFalse(result['fields']['terminal']['known'])

if __name__=='__main__':unittest.main()
