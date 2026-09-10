from __future__ import annotations
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"baseline/pcmmad_receiver/pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"
NEW=ROOT/"baseline/pcmmad_receiver/pcmmad_lab_action_schema_v11_0_capability_microkernel_8.json"
class SchemaV11OpenApiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.schema=json.loads(NEW.read_text(encoding="utf-8")); cls.old=json.loads(OLD.read_text(encoding="utf-8"))
 @staticmethod
 def ops(schema): return [(p,m.upper(),x.get("operationId")) for p,item in schema["paths"].items() for m,x in item.items() if m.lower() in {"get","post","put","patch","delete"}]
 def test_exactly_eight_unique_microkernel_operations(self):
  ops=self.ops(self.schema); self.assertEqual(len(ops),8); self.assertEqual(len({x[2] for x in ops}),8); self.assertEqual({x[2] for x in ops},{"orientCapabilities","invokeCapability","flowCapabilities","composePlan","executePlan","observeRuntime","resumeContinuation","transferData"})
 def test_schema_at_least_70_percent_smaller_than_v10(self): self.assertLess(NEW.stat().st_size,OLD.stat().st_size*0.30)
 def test_flow_reuses_batch_route_but_does_not_expose_legacy_parallel_scheduler(self):
  self.assertIn("/lab/batch",self.schema["paths"]); d=self.schema["paths"]["/lab/batch"]["post"]["description"].lower(); self.assertIn("backward-only",d); self.assertIn("authority refs are forbidden",d); self.assertIn("sequential",d)
  req=self.schema["components"]["schemas"]["FlowBatchRequest"]; self.assertEqual(req["properties"]["parallelism"]["enum"],[1]); self.assertEqual(req["properties"]["steps"]["maxItems"],12)
  step=self.schema["components"]["schemas"]["FlowStep"]; self.assertIn("expected_contract_digest",step["required"])
 def test_invoke_is_escape_hatch_and_authority_separate(self):
  req=self.schema["components"]["schemas"]["InvokeRequest"]; self.assertIn("authority",req["properties"]); self.assertIn("escape hatch",self.schema["paths"]["/lab/vnext/invoke"]["post"]["description"])
 def test_lease_declares_no_authority(self):
  lease=self.schema["components"]["schemas"]["CapabilityLease"]; self.assertEqual(lease["properties"]["authority_effect"]["enum"],["NONE"]); self.assertEqual(lease["properties"]["law"]["enum"],["CAPABILITY_LEASE != CAPABILITY_GRANT"])
 def test_compose_deterministic_and_cost_bounded(self):
  req=self.schema["components"]["schemas"]["ComposeRequest"]; self.assertEqual(req["properties"]["max_cost_units"]["maximum"],320); self.assertEqual(req["properties"]["max_cost_units"]["default"],120); d=req["description"]; self.assertIn("Deterministically",d); self.assertIn("does not synthesize nodes",d); self.assertIn("statically computable cost",d)
 def test_sealed_plan_has_no_temporal_identity_field(self):
  p=self.schema["components"]["schemas"]["CapabilityPlan"]; self.assertNotIn("created_at",p["properties"]); self.assertNotIn("created_at",p["required"])
 def test_sealed_plan_binds_effect_profile_and_cost(self):
  p=self.schema["components"]["schemas"]["CapabilityPlan"]
  for f in ("static_cost_units","max_cost_units","cost_semantics","max_resolved_argument_bytes","effect_profile_digest","effect_catalog_digest"): self.assertIn(f,p["required"]); self.assertIn(f,p["properties"])
 def test_resolved_argument_ceiling_is_explicit(self):
  p=self.schema["components"]["schemas"]["CapabilityPlan"]["properties"]["max_resolved_argument_bytes"]; self.assertEqual(p["enum"],[65536]); self.assertIn("result handle",p["description"])
 def test_observe_projection_excludes_unbounded_full_result_mode(self):
  modes=self.schema["components"]["schemas"]["ObserveRequest"]["properties"]["mode"]["enum"]; self.assertNotIn("full",modes); self.assertTrue({"auto","metadata","preview","range","status","progress","wait","output"}.issubset(set(modes)))
 def test_observe_effect_profile_without_new_endpoint(self):
  kinds=self.schema["components"]["schemas"]["ObserveRequest"]["properties"]["kind"]["enum"]; self.assertIn("effect_profile",kinds); self.assertNotIn("/lab/vnext/effect-profile",self.schema["paths"])
 def test_resume_states_freshness_law(self):
  d=self.schema["components"]["schemas"]["ResumeRequest"]["description"]; self.assertIn("CONTINUATION != CURRENTNESS",d); self.assertIn("re-executed",d)
 def test_plan_node_has_no_authority(self): self.assertNotIn("authority",self.schema["components"]["schemas"]["PlanNode"]["properties"])
 def test_flow_refs_are_payload_only(self): self.assertIn("Refs are payload-only",self.schema["components"]["schemas"]["FlowStep"]["properties"]["payload"]["description"])
 def test_v10_remains_for_compatibility(self): self.assertTrue(OLD.is_file()); self.assertEqual(len(self.ops(self.old)),30)
 def test_all_local_component_refs_resolve(self):
  refs=[]
  def walk(value):
   if isinstance(value,dict):
    if isinstance(value.get("$ref"),str) and value["$ref"].startswith("#/components/schemas/"): refs.append(value["$ref"].rsplit("/",1)[-1])
    for child in value.values(): walk(child)
   elif isinstance(value,list):
    for child in value: walk(child)
  walk(self.schema)
  schemas=self.schema["components"]["schemas"]
  self.assertTrue(refs)
  self.assertEqual(sorted(set(refs)-set(schemas)),[])

 def test_generator_byte_deterministic(self):
  before=NEW.read_bytes(); cp=subprocess.run([sys.executable,"tools/generate_schema_vnext.py"],cwd=ROOT,capture_output=True,text=True,timeout=30); self.assertEqual(cp.returncode,0,cp.stderr); after=NEW.read_bytes(); self.assertEqual(after,before); self.assertEqual(hashlib.sha256(after).hexdigest(),hashlib.sha256(before).hexdigest())
if __name__=="__main__": unittest.main()
