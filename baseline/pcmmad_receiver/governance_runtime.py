"""Server-native deterministic governance/contact and finite-exhaustion mechanics.

This module is deliberately authority-neutral.  It derives and verifies governance
preconditions and exact finite frames; mutation authority remains owned by the
existing project mutation authority plane.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

GRAMMAR_BOOLEAN = "INDEPENDENT_BOOLEAN_BASIS"
GRAMMAR_CONSTRAINED = "CONSTRAINED_FINITE_GRAMMAR"
COMPAT_CROSS = "UNCONDITIONAL_CROSS_PRODUCT"
COMPAT_EXPLICIT = "EXPLICIT_LAWFUL_JOINT_SET"
SEMANTIC_EXTENTS = {"FULL_ARTIFACT", "BOUNDED_SEMANTIC_SECTION", "MACHINE_READBACK", "INTEGRITY_ONLY"}
CURRENTNESS = {"CURRENT", "HISTORICAL_SUPERSEDED", "UNKNOWN", "CONTRADICTORY"}
RELATION_TYPES = {"ALIAS", "IMPLICATION", "EXCLUSION", "COMPOSITE", "MULTI_VALUED_AXIS"}


class GovernanceError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int = 400, extra: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = int(status)
        self.extra = dict(extra or {})


def _fail(code: str, message: str, *, status: int = 400, **extra: Any) -> None:
    raise GovernanceError(code, message, status=status, extra=extra)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        _fail("GOVERNANCE_CONTRACT_INVALID", f"{field} must be a list of non-empty strings")
    return list(value)


def _required(obj: Mapping[str, Any], fields: Sequence[str], context: str) -> None:
    missing = [field for field in fields if field not in obj]
    if missing:
        _fail("GOVERNANCE_CONTRACT_INVALID", f"{context} missing required fields: {missing}")


def _selector_matches(selectors: Mapping[str, Any], task: Mapping[str, Any]) -> bool:
    def intersects(field: str, task_values: Sequence[str]) -> bool:
        values = _strings(selectors.get(field, []), f"selectors.{field}")
        return not values or bool(set(values) & set(task_values))
    if not intersects("mutation_classes", [str(task["mutation_class"])]): return False
    if not intersects("consequence_classes", task["consequence_classes"]): return False
    if not intersects("mechanism_tags", task["mechanism_tags"]): return False
    if not intersects("capabilities", task["capabilities"]): return False
    prefixes = [x.replace("\\", "/") for x in _strings(selectors.get("path_prefixes", []), "selectors.path_prefixes")]
    touched = [x.replace("\\", "/") for x in task["touched_paths"]]
    return not prefixes or any(path.startswith(prefix) for prefix in prefixes for path in touched)


def validate_governance_task(task: Mapping[str, Any]) -> None:
    _required(task, ["task_id", "project_scopes", "mutation_class", "consequence_classes", "mechanism_tags", "touched_paths", "capabilities"], "task")
    if not isinstance(task["task_id"], str) or not task["task_id"]:
        _fail("GOVERNANCE_TASK_INVALID", "task_id must be non-empty")
    for field in ("project_scopes", "consequence_classes", "mechanism_tags", "touched_paths", "capabilities"):
        _strings(task[field], f"task.{field}")
    if not isinstance(task["mutation_class"], str) or not task["mutation_class"]:
        _fail("GOVERNANCE_TASK_INVALID", "mutation_class must be non-empty")


def validate_governance_catalog(catalog: Mapping[str, Any]) -> None:
    _required(catalog, ["project_profiles", "sidecars"], "catalog")
    if not isinstance(catalog["project_profiles"], list) or not isinstance(catalog["sidecars"], list):
        _fail("GOVERNANCE_CATALOG_INVALID", "project_profiles and sidecars must be lists")
    current_profiles: dict[str, str] = {}
    profile_ids: set[str] = set()
    for profile in catalog["project_profiles"]:
        _required(profile, ["profile_id", "project_scope", "currentness", "rules"], "project_profile")
        pid = str(profile["profile_id"]); scope = str(profile["project_scope"])
        if not pid or pid in profile_ids: _fail("GOVERNANCE_CATALOG_INVALID", f"duplicate/empty profile_id: {pid}")
        profile_ids.add(pid)
        currentness = profile["currentness"]
        if not isinstance(currentness, Mapping) or currentness.get("status") not in CURRENTNESS or not str(currentness.get("basis") or ""):
            _fail("GOVERNANCE_CATALOG_INVALID", f"invalid profile currentness: {pid}")
        if currentness["status"] == "CURRENT":
            if scope in current_profiles: _fail("GOVERNANCE_CURRENTNESS_CONTRADICTORY", f"multiple CURRENT profiles for {scope}")
            current_profiles[scope] = pid
        if not isinstance(profile["rules"], list): _fail("GOVERNANCE_CATALOG_INVALID", f"profile rules invalid: {pid}")
        for rule in profile["rules"]:
            _required(rule,["rule_id","selectors","required_authority_classes","required_sidecar_ids"],f"profile {pid} rule")
            if not isinstance(rule["selectors"],Mapping): _fail("GOVERNANCE_CATALOG_INVALID",f"profile {pid} selectors invalid")
            _strings(rule["required_authority_classes"],"required_authority_classes"); _strings(rule["required_sidecar_ids"],"required_sidecar_ids")
    sidecar_ids: set[str] = set(); current_subjects: dict[tuple[str, str], set[str | None]] = {}
    for sidecar in catalog["sidecars"]:
        _required(sidecar, ["sidecar_id", "project_scope", "subject", "authority_class", "currentness", "contact_rules"], "sidecar")
        sid = str(sidecar["sidecar_id"])
        if not sid or sid in sidecar_ids: _fail("GOVERNANCE_CATALOG_INVALID", f"duplicate/empty sidecar_id: {sid}")
        sidecar_ids.add(sid)
        currentness = sidecar["currentness"]
        if not isinstance(currentness, Mapping) or currentness.get("status") not in CURRENTNESS or not str(currentness.get("basis") or ""):
            _fail("GOVERNANCE_CATALOG_INVALID", f"invalid sidecar currentness: {sid}")
        subject = sidecar["subject"]
        if not isinstance(subject, Mapping) or not str(subject.get("locator") or ""):
            _fail("GOVERNANCE_CATALOG_INVALID", f"invalid sidecar subject: {sid}")
        if currentness["status"] == "CURRENT":
            key=(str(sidecar["project_scope"]), str(subject["locator"])); current_subjects.setdefault(key,set()).add(subject.get("sha256"))
        if not isinstance(sidecar["contact_rules"], list): _fail("GOVERNANCE_CATALOG_INVALID", f"invalid contact_rules: {sid}")
        for rule in sidecar["contact_rules"]:
            _required(rule, ["rule_id", "selectors", "contact"], f"sidecar {sid} rule")
            contact=rule["contact"]
            _required(contact,["contact_id","locator","authority_class","semantic_extent","currentness_required","commit_recheck","reason"],f"sidecar {sid} contact")
            if not isinstance(rule["selectors"],Mapping): _fail("GOVERNANCE_CATALOG_INVALID","contact selectors must be an object")
            if contact["semantic_extent"] not in SEMANTIC_EXTENTS: _fail("GOVERNANCE_CATALOG_INVALID", "invalid semantic_extent")
            if not isinstance(contact["currentness_required"],bool): _fail("GOVERNANCE_CATALOG_INVALID","currentness_required must be bool")
            if contact["commit_recheck"] not in {"LOCAL_FILE_SHA256","RECEIPT_BOUND_EXTERNAL"}: _fail("GOVERNANCE_CATALOG_INVALID", "invalid commit_recheck")
            if contact["commit_recheck"] == "LOCAL_FILE_SHA256" and not contact.get("expected_sha256"):
                _fail("GOVERNANCE_CATALOG_INVALID", "LOCAL_FILE_SHA256 requires expected_sha256")
            if contact.get("expected_sha256") is not None:
                h=str(contact["expected_sha256"]).lower()
                if len(h)!=64 or any(ch not in "0123456789abcdef" for ch in h): _fail("GOVERNANCE_CATALOG_INVALID","invalid expected_sha256")
    for key, hashes in current_subjects.items():
        concrete={h for h in hashes if h is not None}
        if len(concrete)>1: _fail("GOVERNANCE_CURRENTNESS_CONTRADICTORY", f"CURRENT sidecars disagree for {key}")


def derive_contact_set(catalog: Mapping[str, Any], task: Mapping[str, Any]) -> dict[str, Any]:
    validate_governance_catalog(catalog); validate_governance_task(task)
    profiles={p["project_scope"]:p for p in catalog["project_profiles"] if p["currentness"]["status"]=="CURRENT"}
    sidecars={s["sidecar_id"]:s for s in catalog["sidecars"]}
    requirements=[]; errors=[]
    for scope in task["project_scopes"]:
        profile=profiles.get(scope)
        if profile is None:
            errors.append({"project_scope":scope,"reason":"MISSING_CURRENT_PROJECT_PROFILE"}); continue
        for rule in profile["rules"]:
            if not _selector_matches(rule.get("selectors",{}), task): continue
            req_classes=_strings(rule.get("required_authority_classes",[]),"required_authority_classes")
            req_sidecars=_strings(rule.get("required_sidecar_ids",[]),"required_sidecar_ids")
            requirements.append({"project_scope":scope,"profile_id":profile["profile_id"],"rule_id":rule["rule_id"],"required_authority_classes":req_classes,"required_sidecar_ids":req_sidecars})
            for cls in req_classes:
                if not any(s["authority_class"]==cls and s["currentness"]["status"]=="CURRENT" and s["project_scope"] in {scope,"*"} for s in catalog["sidecars"]):
                    errors.append({"project_scope":scope,"reason":"MISSING_REQUIRED_AUTHORITY_CLASS","authority_class":cls})
            for sid in req_sidecars:
                if sid not in sidecars or sidecars[sid]["currentness"]["status"]!="CURRENT": errors.append({"project_scope":scope,"reason":"MISSING_OR_NONCURRENT_REQUIRED_SIDECAR","sidecar_id":sid})
    contacts: dict[str,dict[str,Any]]={}
    for sidecar in catalog["sidecars"]:
        if sidecar["project_scope"] not in {"*", *task["project_scopes"]}: continue
        matched=[r for r in sidecar["contact_rules"] if _selector_matches(r["selectors"],task)]
        if not matched: continue
        status=sidecar["currentness"]["status"]
        allow_historical=all(bool(r["selectors"].get("allow_historical")) for r in matched)
        if status=="HISTORICAL_SUPERSEDED" and not allow_historical:
            errors.append({"sidecar_id":sidecar["sidecar_id"],"reason":"MATCHED_HISTORICAL_SIDECAR_FOR_CURRENT_TASK"}); continue
        if status in {"UNKNOWN","CONTRADICTORY"}:
            errors.append({"sidecar_id":sidecar["sidecar_id"],"reason":"MATCHED_SIDECAR_CURRENTNESS_"+status}); continue
        for rule in matched:
            contact=dict(rule["contact"]); contact.update({"origin_sidecar_id":sidecar["sidecar_id"],"origin_rule_id":rule["rule_id"],"sidecar_currentness_status":status,"sidecar_currentness_basis":sidecar["currentness"]["basis"],"project_scope":sidecar["project_scope"]})
            cid=contact["contact_id"]
            if cid in contacts:
                keys=("locator","authority_class","semantic_extent","currentness_required","commit_recheck","expected_sha256")
                if any(contacts[cid].get(k)!=contact.get(k) for k in keys): _fail("GOVERNANCE_CONTACT_CONFLICT",f"conflicting contact definition: {cid}")
                contacts[cid].setdefault("additional_origins",[]).append({"sidecar_id":sidecar["sidecar_id"],"rule_id":rule["rule_id"]})
            else: contacts[cid]=contact
    for req in requirements:
        for cls in req["required_authority_classes"]:
            if not any(c.get("authority_class")==cls for c in contacts.values()): errors.append({"project_scope":req["project_scope"],"reason":"REQUIRED_AUTHORITY_CLASS_DID_NOT_CONTRIBUTE_CONTACT","authority_class":cls})
        for sid in req["required_sidecar_ids"]:
            if not any(c.get("origin_sidecar_id")==sid or any(x.get("sidecar_id")==sid for x in c.get("additional_origins",[])) for c in contacts.values()): errors.append({"project_scope":req["project_scope"],"reason":"REQUIRED_SIDECAR_DID_NOT_CONTRIBUTE_CONTACT","sidecar_id":sid})
    body={"schema":"pcmmad.governance-contact-set.v1","state":"CONTACT_SET_REJECTED" if errors else "CONTACT_SET_DERIVED","task":dict(task),"catalog_digest":digest(catalog),"task_digest":digest(task),"orientation_requirements":requirements,"entries":[contacts[k] for k in sorted(contacts)],"rejection_reasons":errors,"authority_effect":"NONE"}
    body["contact_set_digest"]=digest(body)
    return body


def admit_contact_set(contact_set: Mapping[str, Any], receipts: Sequence[Mapping[str, Any]], *, catalog: Mapping[str, Any], task: Mapping[str, Any], project_root: Path | None = None) -> dict[str, Any]:
    if contact_set.get("state")!="CONTACT_SET_DERIVED": _fail("GOVERNANCE_CONTACT_SET_REJECTED","contact set is not eligible",status=409)
    expected_digest=contact_set.get("contact_set_digest"); basis=dict(contact_set); basis.pop("contact_set_digest",None)
    if expected_digest!=digest(basis): _fail("GOVERNANCE_CONTACT_SET_STALE","contact set digest mismatch",status=409)
    current = derive_contact_set(catalog, task)
    if current.get("state") != "CONTACT_SET_DERIVED": _fail("GOVERNANCE_CONTACT_SET_STALE","current catalog/task no longer derive an admissible contact set",status=409)
    if dict(contact_set) != current: _fail("GOVERNANCE_CONTACT_SET_STALE","contact set differs from current re-derived requirement set",status=409)
    by_id: dict[str,Mapping[str,Any]]={}
    for receipt in receipts:
        cid=str(receipt.get("contact_id") or "")
        if not cid or cid in by_id: _fail("GOVERNANCE_RECEIPT_INVALID",f"duplicate/empty receipt contact_id: {cid}")
        by_id[cid]=receipt
    errors=[]; task=contact_set["task"]; scope="+".join(sorted(task["project_scopes"]))+"|"+task["task_id"]
    for entry in contact_set["entries"]:
        cid=entry["contact_id"]; receipt=by_id.get(cid)
        if receipt is None: errors.append({"contact_id":cid,"error":"MISSING_RECEIPT"}); continue
        checks=(("contact_set_digest",expected_digest,"WRONG_CONTACT_SET"),("locator",entry["locator"],"WRONG_LOCATOR"),("governing_scope",scope,"WRONG_GOVERNING_SCOPE"),("semantic_extent",entry["semantic_extent"],"WRONG_SEMANTIC_EXTENT"))
        for field,want,code in checks:
            if receipt.get(field)!=want: errors.append({"contact_id":cid,"error":code})
        if not str(receipt.get("currentness_basis") or "").strip(): errors.append({"contact_id":cid,"error":"MISSING_CURRENTNESS_BASIS"})
        if str(receipt.get("read_note") or "").strip().upper() in {"","ACK","ACKNOWLEDGED","READ","OK"}: errors.append({"contact_id":cid,"error":"NON_SUBSTANTIVE_ACKNOWLEDGEMENT_NOTE"})
        observed=str(receipt.get("observed_sha256") or "")
        expected=entry.get("expected_sha256")
        if expected and observed!=expected: errors.append({"contact_id":cid,"error":"WRONG_HASH"})
        if entry.get("commit_recheck")=="LOCAL_FILE_SHA256":
            if project_root is None:
                errors.append({"contact_id":cid,"error":"PROJECT_SCOPE_REQUIRED_FOR_LOCAL_RECHECK"})
                continue
            root=project_root.resolve(); raw=Path(str(entry["locator"]))
            locator=(raw if raw.is_absolute() else root/raw).resolve()
            try: locator.relative_to(root)
            except ValueError:
                errors.append({"contact_id":cid,"error":"LOCAL_SOURCE_OUTSIDE_PROJECT_SCOPE"}); continue
            if not locator.is_file(): errors.append({"contact_id":cid,"error":"LOCAL_SOURCE_MISSING_AT_ADMISSION"})
            elif not expected or file_sha256(locator)!=expected: errors.append({"contact_id":cid,"error":"LOCAL_SOURCE_DRIFT_AT_ADMISSION"})
    result={"schema":"pcmmad.governance-contact-admission.v1","state":"CONTACT_SET_REJECTED" if errors else "CONTACT_SET_SATISFIED","contact_set_digest":expected_digest,"task_id":task["task_id"],"required_contacts":len(contact_set["entries"]),"receipt_contacts":len(by_id),"errors":errors,"extra_receipts_ignored":sorted(set(by_id)-{e["contact_id"] for e in contact_set["entries"]}),"authority_effect":"NONE"}
    result["result_digest"]=digest(result)
    return result


def _validate_pressures(pressures: Sequence[Mapping[str, Any]]) -> list[str]:
    ids=[]; labels=[]
    for pressure in pressures:
        _required(pressure,["semantic_id","label","provenance","description"],"pressure")
        ids.append(str(pressure["semantic_id"])); labels.append(str(pressure["label"]))
    if len(ids)!=len(set(ids)): _fail("GRAMMAR_INVALID","duplicate pressure semantic identity")
    if len(labels)!=len(set(labels)): _fail("GRAMMAR_INVALID","duplicate pressure label")
    return ids


def _validate_envs(envs: Sequence[Mapping[str, Any]]) -> list[str]:
    ids=[]
    for env in envs:
        _required(env,["semantic_id","label","provenance"],"environment"); ids.append(str(env["semantic_id"]))
    if len(ids)!=len(set(ids)): _fail("ENVIRONMENT_INVALID","duplicate environment semantic identity")
    return ids


def enumerate_lawful_frame(grammar: Mapping[str, Any], environments: Sequence[Mapping[str, Any]], *, compatibility: Mapping[str, Any] | None = None, budget: int | None = None) -> dict[str, Any]:
    mode=grammar.get("grammar_mode"); pressure_ids=_validate_pressures(grammar.get("pressures") or []); env_ids=_validate_envs(environments)
    if mode==GRAMMAR_BOOLEAN:
        if not str(grammar.get("basis_justification") or "") or not str(grammar.get("basis_evidence_digest") or "") or grammar.get("all_subsets_lawful") is not True:
            _fail("BOOLEAN_BASIS_NOT_PROVEN","independent Boolean basis requires justification, evidence digest, and all_subsets_lawful=true")
        states=[tuple(c) for r in range(len(pressure_ids)+1) for c in combinations(pressure_ids,r)]
    elif mode==GRAMMAR_CONSTRAINED:
        if grammar.get("lawful_state_mode")!="EXPLICIT_FINITE_SET": _fail("GRAMMAR_MODE_UNSUPPORTED","only explicit constrained finite sets are native in v1")
        states=[tuple(x) for x in grammar.get("lawful_state_spec") or []]
        if len(states)!=len(set(states)): _fail("GRAMMAR_INVALID","duplicate lawful pressure state")
        for state in states:
            if not set(state).issubset(set(pressure_ids)): _fail("GRAMMAR_INVALID","lawful state references unknown pressure")
        for relation in grammar.get("relations") or []:
            if relation.get("type") not in RELATION_TYPES: _fail("GRAMMAR_INVALID","unknown relation type")
    else: _fail("GRAMMAR_MODE_UNSUPPORTED",f"unsupported grammar mode: {mode}")
    compat=dict(compatibility or {})
    c_mode=compat.get("compatibility_mode",COMPAT_CROSS if mode==GRAMMAR_BOOLEAN else None)
    if c_mode==COMPAT_CROSS:
        if mode!=GRAMMAR_BOOLEAN: _fail("ENVIRONMENT_COMPATIBILITY_UNPROVEN","constrained grammar cannot assume unconditional cross product")
        joint=[(env,state) for env in env_ids for state in states]
    elif c_mode==COMPAT_EXPLICIT:
        joint=[(str(row[0]),tuple(row[1])) for row in compat.get("lawful_joint_spec") or []]
        if len(joint)!=len(set(joint)): _fail("ENVIRONMENT_INVALID","duplicate lawful joint state")
        for env,state in joint:
            if env not in env_ids or state not in states: _fail("ENVIRONMENT_INVALID","joint spec references unlawful state/environment")
    else: _fail("ENVIRONMENT_COMPATIBILITY_UNPROVEN","explicit/versioned compatibility required")
    required=len(joint); effective_budget=required if budget is None else max(0,int(budget))
    if effective_budget<required:
        return {"state":"DEFER_UNKNOWN_INSUFFICIENT_BUDGET","required_case_count":required,"budget":effective_budget,"evaluations":0,"grammar_digest":digest(grammar),"environment_digest":digest({"environments":list(environments),"compatibility":compat}),"claim_ceiling":"FINITE_GRAMMAR_EXHAUSTED != RESPONSIBILITY_WORLD_EXHAUSTED"}
    cases=[{"case_index":i,"environment_id":env,"pressure_state":list(state),"case_digest":digest({"environment_id":env,"pressure_state":list(state)})} for i,(env,state) in enumerate(joint)]
    return {"state":"EXHAUSTIVE_READY","required_case_count":required,"budget":effective_budget,"evaluations":required,"grammar_digest":digest(grammar),"environment_digest":digest({"environments":list(environments),"compatibility":compat}),"cases":cases,"frame_digest":digest(cases),"claim_ceiling":"FINITE_GRAMMAR_EXHAUSTED != RESPONSIBILITY_WORLD_EXHAUSTED"}


def pareto_relation(frame: Sequence[str], effects: Mapping[str, Any], baseline: Mapping[str, Any]) -> str:
    if set(effects)!=set(frame) or set(baseline)!=set(frame): _fail("INCOMPLETE_RESPONSIBILITY_FRAME","missing or extra responsibility coordinate")
    deltas=[float(effects[k])-float(baseline[k]) for k in frame]
    if all(x==0 for x in deltas): return "EQUAL"
    if all(x>=0 for x in deltas) and any(x>0 for x in deltas): return "STRICT_IMPROVEMENT"
    if all(x<=0 for x in deltas) and any(x<0 for x in deltas): return "STRICT_DEGRADATION"
    return "TRADEOFF"


def evaluate_effect_table(*, frame: Sequence[str], baseline: Mapping[str, Any] | None, baseline_binding: Mapping[str, Any], case_effects: Sequence[Mapping[str, Any]], expected_case_digests: Sequence[str]) -> dict[str, Any]:
    required_binding=("grammar_digest","environment_digest","evaluator_digest","baseline_id","baseline_version","baseline_digest","baseline_current")
    missing=[k for k in required_binding if k not in baseline_binding]
    if missing: _fail("EVALUATOR_BINDING_INCOMPLETE",f"missing evaluator/baseline bindings: {missing}")
    if baseline_binding.get("baseline_current") is not True: _fail("BASELINE_NOT_CURRENT","baseline is not current",status=409)
    if baseline is None: _fail("BASELINE_UNAVAILABLE","baseline unavailable",status=409)
    if len(case_effects)!=len(expected_case_digests): _fail("EXHAUSTION_INCOMPLETE","case effect count does not match lawful frame")
    by_digest={str(row.get("case_digest") or ""):row for row in case_effects}
    if set(by_digest)!=set(expected_case_digests) or len(by_digest)!=len(case_effects): _fail("EXHAUSTION_INCOMPLETE","case identities do not exactly match lawful frame")
    results=[]
    for case_digest in expected_case_digests:
        row=by_digest[case_digest]
        if row.get("status")!="EVALUATED": _fail("EVALUATOR_FAILURE",f"case {case_digest} is not a valid evaluated outcome",status=409)
        effects=row.get("effects")
        if not isinstance(effects,Mapping): _fail("EFFECTS_UNAVAILABLE",f"effects unavailable for {case_digest}",status=409)
        relation=pareto_relation(frame,effects,baseline)
        results.append({"case_digest":case_digest,"effects":dict(effects),"baseline":dict(baseline),"changed":dict(effects)!=dict(baseline),"pareto_relation":relation})
    proof={"schema":"pcmmad.finite-exhaustion-proof.v1","state":"EXHAUSTED_DECLARED_FRAME","binding":dict(baseline_binding),"responsibility_frame":list(frame),"case_count":len(results),"results":results,"claim_ceiling":"FINITE_GRAMMAR_EXHAUSTED != RESPONSIBILITY_WORLD_EXHAUSTED"}
    proof["proof_digest"]=digest(proof)
    return proof


def compress_minimal_witnesses(*, cases: Sequence[Mapping[str, Any]], witness_case_digests: Sequence[str], inherit_supersets: bool = False, monotonicity_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    by_digest={str(c.get("case_digest") or ""):c for c in cases}
    wanted=set(str(x) for x in witness_case_digests)
    if not wanted.issubset(set(by_digest)):
        _fail("WITNESS_INVALID","witness references case outside lawful frame")
    if inherit_supersets:
        evidence=dict(monotonicity_evidence or {})
        required=("property_id","relation_digest","state_order_digest","proof_or_evidence_digest","scope")
        if any(not str(evidence.get(k) or "") for k in required):
            _fail("MONOTONICITY_EVIDENCE_REQUIRED","superset inheritance requires explicit monotonicity evidence")
    minimal=[]
    for case_digest in sorted(wanted):
        case=by_digest[case_digest]; env=str(case.get("environment_id") or ""); state=set(case.get("pressure_state") or [])
        dominated=False
        for other_digest in wanted:
            if other_digest==case_digest: continue
            other=by_digest[other_digest]
            if str(other.get("environment_id") or "")!=env: continue
            other_state=set(other.get("pressure_state") or [])
            if other_state < state:
                dominated=True; break
        if not dominated: minimal.append(case_digest)
    result={"schema":"pcmmad.minimal-witness-antichain.v1","state":"MINIMAL_WITNESSES_COMPRESSED","minimality_domain":"LAWFUL_SEMANTIC_STATE_ORDER","input_witness_count":len(wanted),"minimal_witness_count":len(minimal),"minimal_case_digests":minimal,"complete_frame_digest":digest(list(cases)),"superset_inheritance":bool(inherit_supersets),"monotonicity_evidence":dict(monotonicity_evidence or {}) if inherit_supersets else None,"claim_ceiling":"MINIMAL_WITNESS_ANTICHAIN != SAFE_SUPERSET_INHERITANCE_WITHOUT_MONOTONICITY"}
    result["result_digest"]=digest(result)
    return result
