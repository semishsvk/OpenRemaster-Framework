"""Synthetic claim tests; no external receipt or independent verifier is simulated as trusted."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from glca.core import Hold,digest
from intake_bridge import (SCHEMA,CANONICAL_CHECKS,ROLE_CHECKS,PAIR_CHECKS,PRINCIPAL_CHECKS,
                           FALSE_FLAGS,ZERO,inspect_report,read_report)
from master_workflow import advisory_package

def context():return dict(operation_id='synthetic-operation',project_id='fixture',capability='source.analysis',
                          work_package_sha256='a'*64,packet_sha256='b'*64)
def row(checks):return dict(present=True,status='PASS',failures=[],checks={k:True for k in checks})
def fixture():
    binding={k:v for k,v in context().items() if k!='packet_sha256'}
    binding.update(packet_sha256_observed='b'*64,checks={k:True for k in CANONICAL_CHECKS})
    evidence={k:row(checks) for k,checks in ROLE_CHECKS.items()}
    evidence['owner_witness_evidence']=row(PAIR_CHECKS)
    return dict(schema=SCHEMA,canonical=binding,evidence=evidence,
                manifest=row(('schema','operation_binding','work_package_binding','owner_witness_mode')),
                status='PASS_LIVE_AUTHORITY_INTAKE_NO_DISPATCH',intake_ready=True,read_only=True,
                failures=[],missing_external_evidence=[],rejected_external_evidence=[],
                **{key:False for key in FALSE_FLAGS})

class IntakeBridgeTests(unittest.TestCase):
    def safe(self,result):
        self.assertIn(result['status'],('HOLD','REJECT'))
        for flag in ZERO:self.assertIs(result[flag],False)
    def test_complete_claims_never_authorize(self):
        r=inspect_report(fixture(),context());self.safe(r)
        self.assertTrue(r['structural_claims_consistent'])
        self.assertIn('INDEPENDENT_CRYPTO_OWNER_LEASE_GOVERNOR_REVALIDATION_REQUIRED',r['reasons'])
    def test_all_context_bindings(self):
        for key in context():
            with self.subTest(key=key):
                report=fixture();report['canonical']['packet_sha256_observed' if key=='packet_sha256' else key]='different'
                r=inspect_report(report,context());self.safe(r);self.assertEqual(r['status'],'REJECT')
                self.assertIn('CONTEXT_MISMATCH:'+key,r['reasons'])
    def test_every_authority_flag_is_strict(self):
        for key in FALSE_FLAGS:
            for value in (True,None,0,'false'):
                with self.subTest(flag=key,value=value):
                    report=fixture();report[key]=value
                    self.assertEqual(inspect_report(report,context())['status'],'REJECT')
    def test_missing_rows_with_false_ready_claim_rejected(self):
        for key in fixture()['evidence']:
            report=fixture();report['evidence'][key]=dict(present=False,status='MISSING',checks={},failures=[])
            report['missing_external_evidence']=[key]
            self.assertIn('FALSE_READY_CLAIM',inspect_report(report,context())['reasons'])
    def test_reported_missing_rows_hold_without_relabeling(self):
        report=fixture();report.update(status='WAITING_FOR_EXTERNAL_AUTHORITY_EVIDENCE',intake_ready=False)
        for key in report['evidence']:report['evidence'][key]=dict(present=False,status='MISSING',checks={},failures=[])
        report['missing_external_evidence']=list(report['evidence']);report['failures']=['missing:'+k for k in report['evidence']]
        r=inspect_report(report,context());self.safe(r);self.assertEqual(r['status'],'HOLD')
    def test_unknown_empty_failed_or_truthy_checks_cannot_pass(self):
        for checks in ({},{'schema':True},{'schema':'PASS'},{'schema':1},{'schema':False},None):
            report=fixture();report['evidence']['k003_admission_receipt']['checks']=checks
            r=inspect_report(report,context());self.safe(r);self.assertFalse(r['structural_claims_consistent'])
    def test_negative_additional_check_cannot_be_ignored(self):
        report=fixture();report['evidence']['host_health_receipt']['checks']['new_gate']=False
        self.assertFalse(inspect_report(report,context())['structural_claims_consistent'])
    def test_separate_owner_witness_shape(self):
        report=fixture();pair=report['evidence']['owner_witness_evidence']
        pair.update(checks={},subevidence={k:row(PRINCIPAL_CHECKS) for k in ('owner_receipt','witness_receipt')})
        r=inspect_report(report,context());self.safe(r);self.assertTrue(r['structural_claims_consistent'])
        del pair['subevidence']['witness_receipt']
        self.assertFalse(inspect_report(report,context())['structural_claims_consistent'])
    def test_manifest_failure_and_summary_contradictions(self):
        for mutation in ('manifest','missing','failed','ready','status'):
            report=fixture()
            if mutation=='manifest':report['manifest']['status']='REJECTED'
            if mutation=='missing':report['missing_external_evidence']=['made-up']
            if mutation=='failed':report['failures']=['stale']
            if mutation=='ready':report['intake_ready']=False
            if mutation=='status':report['status']='ADMITTED'
            self.assertFalse(inspect_report(report,context())['structural_claims_consistent'])
    def test_unknown_report_schema_and_nonfinite_values(self):
        for report in (None,[],{},dict(schema='other'),{'value':float('nan')}):
            r=inspect_report(report,context());self.safe(r);self.assertEqual(r['status'],'REJECT')
    def test_invalid_expected_context(self):
        for expected in (None,{},dict(context(),work_package_sha256='main'),dict(context(),extra='unknown')):
            self.assertEqual(inspect_report(fixture(),expected)['status'],'REJECT')
    def test_bound_reader_and_hash_drift(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'snapshot.json';raw=json.dumps(fixture()).encode();path.write_bytes(raw)
            sha=hashlib.sha256(raw).hexdigest();self.safe(read_report(path,sha,context()))
            self.assertIn('REPORT_HASH_MISMATCH',read_report(path,'0'*64,context())['reasons'])
            self.assertEqual(path.read_bytes(),raw)
    def test_duplicate_json_and_nonfinite_reader_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'snapshot.json'
            for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'not-json'):
                path.write_bytes(raw);r=read_report(path,hashlib.sha256(raw).hexdigest(),context())
                self.assertEqual(r['status'],'REJECT')
    def test_source_paths_in_report_are_never_followed(self):
        report=fixture();report['canonical']['contract']='DO_NOT_OPEN';report['manifest']['path']='../../DO_NOT_OPEN'
        self.safe(inspect_report(report,context()))
    def test_inputs_not_mutated(self):
        report=fixture();before=copy.deepcopy(report);inspect_report(report,context());self.assertEqual(report,before)
    def test_advisory_package_binds_report_changes(self):
        tasks=[dict(id='decode',project='fixture',depends=[])]
        def call(report):return advisory_package('fixture',tasks,[],['script'],'c'*64,intake_report=report,intake_context=context())
        a=call(fixture());report=fixture();report['evidence']['host_health_receipt']['checks']['freshness_verified']=False
        b=call(report);self.assertNotEqual(a['proposal_digest'],b['proposal_digest'])
        self.assertFalse(a['may_dispatch']);self.assertFalse(b['may_dispatch'])
    def test_advisory_cannot_attach_foreign_project(self):
        with self.assertRaisesRegex(Hold,'PROJECT_MISMATCH'):
            advisory_package('foreign',[],[],['script'],'c'*64,intake_report=fixture(),intake_context=context())
    def test_legacy_proposal_digest_preserved_without_new_inputs(self):
        r=advisory_package('fixture',[],[],['script'],'c'*64)
        self.assertEqual(r['proposal_digest'],digest(['fixture',[],[],['script'],'c'*64,'UNKNOWN']))
    def test_development_receipt_changes_invalidate_advice(self):
        a=dict(schema='OpenRemaster.DevWorkflowResult.v1',production_go=False)
        b=dict(a,extra='changed')
        ra=advisory_package('fixture',[],[],['script'],'c'*64,dev_receipt=a)
        rb=advisory_package('fixture',[],[],['script'],'c'*64,dev_receipt=b)
        self.assertNotEqual(ra['proposal_digest'],rb['proposal_digest'])

if __name__=='__main__':unittest.main(verbosity=2)
