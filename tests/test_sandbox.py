"""Tests for redesigned Micro-VM Sandbox architecture with Knowledge & Memory Department."""

from lab.sandbox import (
    ALL_DEPARTMENTS,
    ALL_SPECIALISTS,
    DEPARTMENT_HIERARCHY,
    EXECUTION_DEPARTMENTS,
    MEMORY_DEPARTMENTS,
    CommonKnowledgeHub,
    MicroVMManager,
)


def test_redesigned_department_hierarchy_taxonomy():
    assert len(ALL_DEPARTMENTS) == 6
    assert set(EXECUTION_DEPARTMENTS) == {
        "literature", "hypothesis", "planning", "analysis", "review_safety"
    }
    assert set(MEMORY_DEPARTMENTS) == {"knowledge_memory"}

    assert len(ALL_SPECIALISTS) == 18
    assert set(DEPARTMENT_HIERARCHY["knowledge_memory"]["specialists"]) == {
        "consolidation_agent", "epistemic_agent", "retrieval_agent"
    }


def test_common_knowledge_hub_lifecycle(tmp_path):
    storage = tmp_path / "test_common_knowledge.json"
    hub = CommonKnowledgeHub(storage_path=storage)

    # 1. Literature records a fact
    hub.record_finding("literature", {
        "kind": "fact",
        "claim": "Raman et al. 2014 achieved 40.1 W/m^2 using HfO2/SiO2 on Ag",
        "citation": "10.1038/nature13883"
    })

    # 2. Hypothesis records a hypothesis
    hub.record_finding("hypothesis", {
        "kind": "hypothesis",
        "id": "H1",
        "claim": "SiO2 + Al2O3 covers 8-13 um window without expensive HfO2",
        "status": "proposed"
    })

    # 3. Planning records a simulation run
    hub.record_finding("planning", {
        "kind": "simulation",
        "design": {"materials": ["SiO2", "Al2O3"], "thicknesses_nm": [400.0, 250.0], "substrate": "Ag"},
        "p_net_w_m2": 24.5,
        "valid": True
    })

    # 4. Analysis records a verdict supporting H1
    hub.record_finding("analysis", {
        "kind": "verdict",
        "hypothesis_id": "H1",
        "status": "supported",
        "note": "24.5 W/m^2 exceeds target 11.83 W/m^2"
    })

    assert hub.state.best_p_net_w_m2 == 24.5
    assert hub.state.hypotheses["H1"]["status"] == "supported"

    # Advance to next cycle
    next_context = hub.advance_reasoning_cycle(summary_note="H1 supported, achieved 24.5 W/m^2")
    assert next_context["current_cycle"] == 1
    assert hub.state.cycle == 2
    assert next_context["target_met"] is True
    assert "H1" in next_context["epistemic_summary"]["open_hypotheses"] or next_context["epistemic_summary"]["supported_count"] == 1


def test_microvm_manager_hub_and_spoke_mode():
    mgr = MicroVMManager(default_backend="mock")
    # Say Person 3 decides to spawn 4 micro-VMs: 1 Knowledge Hub + 3 Execution Workers
    vms = mgr.spawn_sandboxes(count=4)
    assert len(vms) == 4

    role_types = [vm.role_type for vm in vms]
    assert role_types.count("knowledge_hub") == 1
    assert role_types.count("execution_worker") == 3

    hub_vm = next(vm for vm in vms if vm.role_type == "knowledge_hub")
    assert hub_vm.department == "knowledge_memory"

    mgr.teardown_all()
    assert len(mgr.list_sandboxes()) == 0


def test_microvm_manager_departmental_mesh_mode():
    mgr = MicroVMManager(default_backend="mock")
    # 6 micro-VMs: 5 execution departments + 1 Knowledge & Memory Hub
    vms = mgr.spawn_sandboxes(count=6)
    assert len(vms) == 6

    depts = {vm.department for vm in vms}
    assert depts == set(ALL_DEPARTMENTS)
    mgr.teardown_all()


def test_sandbox_simulation_pipes_to_common_knowledge(tmp_path):
    mgr = MicroVMManager(default_backend="mock", workspace_dir=tmp_path)
    # Re-wire knowledge hub storage to tmp_path
    mgr.knowledge_hub = CommonKnowledgeHub(storage_path=tmp_path / "ck.json")

    vms = mgr.spawn_sandboxes(count=2)
    worker_vm = next(vm for vm in vms if vm.role_type == "execution_worker")

    res = mgr.run_simulation_in_sandbox(
        name=worker_vm.name,
        materials=["SiO2", "MgF2"],
        thicknesses_nm=[200.0, 300.0],
        substrate="Ag",
    )

    assert res["valid"] is True
    # Verify it automatically piped into the Common Knowledge Hub
    assert len(mgr.knowledge_hub.state.simulations) == 1
    assert mgr.knowledge_hub.state.best_p_net_w_m2 is not None

    # Advance cycle feeds to next reasoning cycle
    context = mgr.advance_cycle("Initial screening complete")
    assert context["total_simulations"] == 1
    mgr.teardown_all()
