from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_ci_consumes_csc_and_final_polish():
 s=(ROOT/'.github/workflows/ci.yml').read_text();assert 'csc_code_health_gate.py' in s and 'final_polish_gate.py' in s
def test_release_verifier_consumes_csc_code_health():assert 'csc_code_health_contract' in (ROOT/'tools/verify_release.py').read_text()
def test_final_polish_invokes_csc():assert 'csc_code_health_gate.py' in (ROOT/'tools/final_polish_gate.py').read_text()
def test_reseal_tool_exists_for_rollover_dependency():assert (ROOT/'tools/reseal_handoff_snapshot.py').is_file()

def test_ci_consumes_declaration_binding(): assert 'csc_declaration_binding_gate.py' in (ROOT/'.github/workflows/ci.yml').read_text()
def test_final_polish_consumes_declaration_binding(): assert 'csc_declaration_binding_gate.py' in (ROOT/'tools/final_polish_gate.py').read_text()
