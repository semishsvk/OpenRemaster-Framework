"""NW024 deterministic OFFLINE Governor proposals, never OS scheduling.

Synthetic telemetry only. No process enumeration, CPU/GPU drivers,
suspension, Windows task actions, K003 calls, production queue or dispatch.
An observed game triggers LIGHT/GAMING by default; override disables
automatic game detection but never overrides thermal/resource emergency.
Unknown task outcome always HOLD_NO_AUTORETRY.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Mode=Literal["NORMAL","LIGHT_GAMING","EMERGENCY_HOLD"]
@dataclass(frozen=True)
class Telemetry:
 cpu_pct:float
 gpu_pct:float
 ram_pct:float
 vram_pct:float
 cpu_temp_c:float
 gpu_temp_c:float
 game_detected:bool
 def __post_init__(self):
  for name in ("cpu_pct","gpu_pct","ram_pct","vram_pct"):
   value=getattr(self,name)
   if type(value) not in (float,int) or not 0<=value<=100:
    raise ValueError("INVALID_TELEMETRY_"+name)
  for name in ("cpu_temp_c","gpu_temp_c"):
   value=getattr(self,name)
   if type(value) not in (float,int) or not 0<=value<=125:
    raise ValueError("INVALID_TEMPERATURE_"+name)
  if type(self.game_detected) is not bool:raise ValueError("INVALID_GAME_FLAG")
@dataclass(frozen=True)
class Job:
 job_id:str
 heavy:bool
 checkpointable:bool
 state:Literal["WAITING","RUNNING","PAUSED","UNKNOWN","FINISHED"]
 checkpoint_sha256:str|None=None
 def __post_init__(self):
  if not self.job_id or not self.job_id.replace("_","").replace("-","").isalnum():
   raise ValueError("INVALID_JOB_ID")
  if type(self.heavy) is not bool or type(self.checkpointable) is not bool:
   raise ValueError("INVALID_JOB_FLAGS")
  if self.state not in ("WAITING","RUNNING","PAUSED","UNKNOWN","FINISHED"):
   raise ValueError("INVALID_JOB_STATE")
  if self.checkpoint_sha256 is not None and (
     type(self.checkpoint_sha256) is not str or len(self.checkpoint_sha256)!=64 or
     any(c not in "0123456789abcdef" for c in self.checkpoint_sha256)):
   raise ValueError("INVALID_CHECKPOINT_SHA")
@dataclass(frozen=True)
class Proposal:
 mode:Mode
 reason_codes:tuple[str,...]
 pause:tuple[str,...]
 admit:tuple[str,...]
 resume:tuple[str,...]
 hold:tuple[str,...]
 max_heavy:int
 may_dispatch:bool=False
 real_processes_mutated:bool=False
class Governor:
 def __init__(self,*,auto_game_detection=True,max_heavy=3):
  if type(auto_game_detection) is not bool:raise ValueError("INVALID_GAME_SETTING")
  if type(max_heavy) is not int or max_heavy!=3:raise ValueError("GLOBAL_HEAVY_CAP_MUST_BE_THREE")
  self.auto_game_detection=auto_game_detection
  self.max_heavy=max_heavy
 def mode(self,t:Telemetry)->tuple[Mode,tuple[str,...]]:
  reasons=[]
  if t.cpu_temp_c>=90 or t.gpu_temp_c>=88:
   reasons.append("THERMAL_LIMIT")
  if t.ram_pct>=95 or t.vram_pct>=95:
   reasons.append("MEMORY_PRESSURE_CRITICAL")
  if reasons:return "EMERGENCY_HOLD",tuple(reasons)
  if self.auto_game_detection and t.game_detected:
   reasons.append("AUTO_GAME_DETECTED")
  if t.cpu_pct>=90 or t.gpu_pct>=90 or t.ram_pct>=88 or t.vram_pct>=90:
   reasons.append("HIGH_RESOURCE_LOAD")
  if reasons:return "LIGHT_GAMING",tuple(reasons)
  return "NORMAL",("RESOURCE_CAPACITY_AVAILABLE",)
 def plan(self,t:Telemetry,jobs:list[Job])->Proposal:
  if type(jobs) is not list:raise ValueError("INVALID_JOBS")
  ids=[j.job_id for j in jobs]
  if len(ids)!=len(set(ids)):raise ValueError("DUPLICATE_JOB")
  mode,reasons=self.mode(t)
  pause=[];admit=[];resume=[];hold=[]
  active=sum(j.heavy and j.state=="RUNNING" for j in jobs)
  if active>self.max_heavy:raise ValueError("HEAVY_CAP_ALREADY_EXCEEDED")
  for j in jobs:
   if j.state=="UNKNOWN":
    hold.append(j.job_id);continue
   if j.state=="RUNNING" and j.heavy and mode!="NORMAL":
    if j.checkpointable:
     pause.append(j.job_id)
    else:
     hold.append(j.job_id)  # no force-kill; cooperative HOLD only
   if j.state=="PAUSED":
    if mode=="NORMAL" and j.checkpointable and j.checkpoint_sha256 is not None:
     if j.heavy and active>=self.max_heavy:continue
     resume.append(j.job_id)
     if j.heavy:active+=1
    elif mode=="NORMAL" and j.checkpoint_sha256 is None:
     hold.append(j.job_id)
   if j.state=="WAITING" and mode=="NORMAL":
    if j.heavy and active>=self.max_heavy:continue
    admit.append(j.job_id)
    if j.heavy:active+=1
  return Proposal(mode,reasons,tuple(pause),tuple(admit),tuple(resume),
                  tuple(dict.fromkeys(hold)),self.max_heavy)
