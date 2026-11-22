"""M010 isolated SQLite crash/recovery laboratory. NEVER production authority.

A durable local diagnostic ledger for M009 candidate operations. Confirmation
is a *caller-supplied review claim*, not an authenticated remote commit.
Every outcome is non-authorizing, including COMMIT_RECORDED_REVIEW_ONLY.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from pathlib import Path

SCHEMA = 'ORF-M010.DurableRecoveryLab.v1'
HEX = set('0123456789abcdef')
class RecoveryHold(ValueError): pass

# Synthetic crash hooks; never a native-job control surface.
PREPARE_FAILURE_POINTS = frozenset(('BEFORE_PREPARE_COMMIT', 'AFTER_PREPARE_COMMIT'))
RECONCILE_FAILURE_POINTS = frozenset(('AFTER_HEAD_UPDATE_BEFORE_COMMIT', 'AFTER_RECONCILE_COMMIT'))

def _failure(point, at):
    if point == at:
        raise RecoveryHold('synthetic failure injected: ' + at)

def digest(value):
    if type(value) is not str or len(value)!=64 or any(c not in HEX for c in value):
        raise RecoveryHold('invalid sha256 digest')
    return value

def number(value, minimum=0):
    if type(value) is not int or not minimum <= value < 2**63-1:
        raise RecoveryHold('invalid monotonic integer')
    return value

class DurableReviewLedger:
    def __init__(self, directory):
        root=Path(directory)
        if not root.is_dir() or root.is_symlink():
            raise RecoveryHold('explicit isolated directory required')
        self.path=root/'m010-review-only.sqlite3'
        if self.path.is_symlink():
            raise RecoveryHold('refusing symlinked ledger')
        self.db=sqlite3.connect(str(self.path), timeout=2, isolation_level=None)
        self.db.execute('PRAGMA busy_timeout=2000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS head (scope TEXT PRIMARY KEY, sequence INTEGER NOT NULL, epoch INTEGER NOT NULL, fence INTEGER NOT NULL, digest TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS operations (op TEXT PRIMARY KEY, scope TEXT NOT NULL, challenge TEXT NOT NULL UNIQUE, prior_digest TEXT NOT NULL, candidate_digest TEXT NOT NULL, sequence INTEGER NOT NULL, epoch INTEGER NOT NULL, fence INTEGER NOT NULL, state TEXT NOT NULL, receipt_digest TEXT, UNIQUE(scope,sequence))')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)',('schema',SCHEMA))
        if self.db.execute('SELECT v FROM meta WHERE k=?',('schema',)).fetchone()!=(SCHEMA,):
            raise RecoveryHold('schema mismatch')

    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self,*_): self.close()
    def _begin(self): self.db.execute('BEGIN IMMEDIATE')
    def _rollback(self): self.db.execute('ROLLBACK')
    def initialize(self,scope,sequence,epoch,fence,head_digest):
        if not isinstance(scope,str) or not scope.isascii() or not 3<=len(scope)<=128 or not all(x.isalnum() or x in '._-' for x in scope): raise RecoveryHold('bad scope')
        number(sequence);number(epoch);number(fence);digest(head_digest)
        self._begin()
        try:
            existing=self.db.execute('SELECT sequence,epoch,fence,digest FROM head WHERE scope=?',(scope,)).fetchone()
            wanted=(sequence,epoch,fence,head_digest)
            if existing is None: self.db.execute('INSERT INTO head VALUES (?,?,?,?,?)',(scope,*wanted))
            elif existing!=wanted: raise RecoveryHold('cannot reset or roll back persisted head')
            self.db.execute('COMMIT')
        except BaseException:
            self._rollback();raise

    def prepare(self,*,op,scope,challenge,prior_digest,candidate_digest,sequence,epoch,fence,failpoint=None):
        if failpoint is not None and failpoint not in PREPARE_FAILURE_POINTS:
            raise RecoveryHold('invalid test-only prepare failure point')
        for value in (op,challenge):
            if not isinstance(value,str) or not value.isascii() or not 8<=len(value)<=128 or not all(x.isalnum() or x in '._-' for x in value): raise RecoveryHold('invalid operation/challenge')
        digest(prior_digest);digest(candidate_digest)
        for v in (sequence,epoch,fence): number(v,1)
        self._begin()
        try:
            head=self.db.execute('SELECT sequence,epoch,fence,digest FROM head WHERE scope=?',(scope,)).fetchone()
            if head is None or prior_digest!=head[3] or sequence!=head[0]+1 or epoch<head[1] or epoch>head[1]+1 or fence<=head[2]: raise RecoveryHold('stale or unbound candidate')
            if self.db.execute('SELECT 1 FROM operations WHERE scope=?',(scope,)).fetchone(): raise RecoveryHold('unresolved or prior operation; explicit reconciliation required')
            try:
                self.db.execute('INSERT INTO operations VALUES (?,?,?,?,?,?,?,?,?,NULL)',(op,scope,challenge,prior_digest,candidate_digest,sequence,epoch,fence,'PREPARED'))
            except sqlite3.IntegrityError as exc: raise RecoveryHold('reused operation or challenge') from exc
            _failure(failpoint, 'BEFORE_PREPARE_COMMIT')
            self.db.execute('COMMIT')
        except BaseException:
            self._rollback();raise
        _failure(failpoint, 'AFTER_PREPARE_COMMIT')
        return self.status(scope)

    def mark_unknown(self,op):
        self._begin()
        try:
            row=self.db.execute('SELECT state FROM operations WHERE op=?',(op,)).fetchone()
            if row is None or row[0] not in ('PREPARED','UNKNOWN'): raise RecoveryHold('cannot mark finalized/missing operation unknown')
            self.db.execute("UPDATE operations SET state='UNKNOWN' WHERE op=?",(op,))
            self.db.execute('COMMIT')
        except BaseException:
            self._rollback();raise

    def reconcile(self,op,*,outcome,receipt_digest=None,failpoint=None):
        # This models a remote reply. No caller-provided value is trusted authority.
        if failpoint is not None and failpoint not in RECONCILE_FAILURE_POINTS:
            raise RecoveryHold('invalid test-only reconcile failure point')
        if outcome not in ('COMMIT_CONFIRMED','REJECTED','UNKNOWN'): raise RecoveryHold('unsupported outcome')
        if outcome=='COMMIT_CONFIRMED': digest(receipt_digest)
        elif receipt_digest is not None: raise RecoveryHold('receipt only for confirmed candidate')
        self._begin()
        try:
            row=self.db.execute('SELECT scope,prior_digest,candidate_digest,sequence,epoch,fence,state,receipt_digest FROM operations WHERE op=?',(op,)).fetchone()
            if row is None or row[6] not in ('PREPARED','UNKNOWN'): raise RecoveryHold('missing/finalized operation')
            scope,prior,candidate,seq,epoch,fence,state,_=row
            if outcome=='COMMIT_CONFIRMED':
                head=self.db.execute('SELECT sequence,epoch,fence,digest FROM head WHERE scope=?',(scope,)).fetchone()
                if head is None or head[3]!=prior or head[0]+1!=seq or epoch<head[1] or fence<=head[2]: raise RecoveryHold('head moved; never infer commit')
                self.db.execute('UPDATE head SET sequence=?,epoch=?,fence=?,digest=? WHERE scope=?',(seq,epoch,fence,candidate,scope))
                self.db.execute("UPDATE operations SET state='COMMIT_RECORDED_REVIEW_ONLY',receipt_digest=? WHERE op=?",(receipt_digest,op))
                _failure(failpoint, 'AFTER_HEAD_UPDATE_BEFORE_COMMIT')
            elif outcome=='REJECTED':
                self.db.execute("UPDATE operations SET state='REJECTED' WHERE op=?",(op,))
            else: self.db.execute("UPDATE operations SET state='UNKNOWN' WHERE op=?",(op,))
            self.db.execute('COMMIT')
        except BaseException:
            self._rollback();raise
        _failure(failpoint, 'AFTER_RECONCILE_COMMIT')

    def status(self,scope):
        head=self.db.execute('SELECT sequence,epoch,fence,digest FROM head WHERE scope=?',(scope,)).fetchone()
        rows=self.db.execute('SELECT op,state FROM operations WHERE scope=? ORDER BY rowid',(scope,)).fetchall()
        return {'schema':SCHEMA,'head':head,'operations':rows,'external_current_head_verified':False,'native_worker_dispatch_authorized':False,'recovery_status':'REVIEW_ONLY_HOLD'}
