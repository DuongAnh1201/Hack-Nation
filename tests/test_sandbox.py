"""Tests for Micro-VM Sandbox manager and hierarchy integration."""

from lab.sandbox import (
    ALL_DEPARTMENTS,
    ALL_SPECIALISTS,
    DEPARTMENT_HIERARCHY,
    MicroVMManager,
)


def test_department_hierarchy_taxonomy():
    assert len(ALL_DEPARTMENTS) == 5
    assert "literature" in DEPARTMENT_HIERARCHY
    assert "hypothesis" in DEPARTMENT_HIERARCHY
    assert "planning" in DEPARTMENT_HIERARCHY
    assert "analysis" in DEPARTMENT_HIERARCHY
    assert "review_safety" in DEPARTMENT_HIERARCHY

    assert len(ALL_SPECIALISTS) == 15
    assert set(DEPARTMENT_HIERARCHY["literature"]["specialists"]) == {
        "search_agent", "citation_agent", "benchmark_agent"
    }
    assert set(DEPARTMENT_HIERARCHY["hypothesis"]["specialists"]) == {
        "physics_agent", "material_agent", "design_agent"
    }
    assert set(DEPARTMENT_HIERARCHY["planning"]["specialists"]) == {
        "cost_agent", "explore_agent", "exploit_agent"
    }
    assert set(DEPARTMENT_HIERARCHY["analysis"]["specialists"]) == {
        "stats_agent", "compare_agent", "failure_agent"
    }
    assert set(DEPARTMENT_HIERARCHY["review_safety"]["specialists"]) == {
        "evidence_agent", "claim_agent", "approval_agent"
    }


def test_microvm_manager_spawn_department_mode():
    mgr = MicroVMManager(default_backend="mock")
    vms = mgr.spawn_sandboxes(count=5)
    assert len(vms) == 5
    depts = {vm.department for vm in vms}
    assert depts == set(ALL_DEPARTMENTS)
    assert len(mgr.list_sandboxes()) == 5
    mgr.teardown_all()
    assert len(mgr.list_sandboxes()) == 0


def test_microvm_manager_spawn_specialist_mode():
    mgr = MicroVMManager(default_backend="mock")
    vms = mgr.spawn_sandboxes(count=15)
    assert len(vms) == 15
    assigned = [vm.assigned_roles[0] for vm in vms]
    assert set(assigned) == set(ALL_SPECIALISTS)
    mgr.teardown_all()


def test_microvm_manager_simulation_execution():
    mgr = MicroVMManager(default_backend="mock")
    vms = mgr.spawn_sandboxes(count=1)
    vm_name = vms[0].name

    res = mgr.run_simulation_in_sandbox(
        name=vm_name,
        materials=["SiO2", "MgF2"],
        thicknesses_nm=[200.0, 300.0],
        substrate="Ag",
    )
    assert res["valid"] is True
    assert "p_net_w_m2" in res
    assert "solar_reflectance" in res
    assert "window_emissivity" in res
    mgr.teardown_all()
