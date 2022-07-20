"""Test writing control.in files for Aims using ase.io.aims.

Control.in file contains calculation parameters such as the functional and
k grid as well as basis set size parameters. We write this file to a string
and assert we find expected values.
"""
import re
from pathlib import Path
from io import StringIO
import pytest
from ase.io.aims import write_control
from ase.build import bulk
from ase.calculators.aims import AimsCube


parent = Path(__file__).parent


_PARAMETERS_DICT = {
    "xc": "LDA",
    "kpts": [2, 2, 2],
    "smearing": ("gaussian", 0.1),
    "output": ["dos 0.0 10.0 101 0.05", "hirshfeld"],
    "dos_kgrid_factors": [21, 21, 21],
    "vdw_correction_hirshfeld": True,
    "compute_forces": True,
    "output_level": "MD_light",
    "charge": 0.0,
    "species_dir": f"{parent}/species_dir/"}


def contains(pattern, txt):
    return re.search(pattern, txt, re.M)

@pytest.fixture
def create_au_bulk_atoms_obj():
    return bulk("Au")

def test_control(create_au_bulk_atoms_obj):
    """Tests that control.in for a Gold bulk system works.
    
    This test tests several things simulationeously, much of
    the aims IO functionality for writing the conrol.in file, such as adding an
    AimsCube to the system.
    """
    # Copy the global parameters dicitonary to avoid rewriting common parameters.
    parameters = _PARAMETERS_DICT.copy()
     # Add AimsCube to the parameter dictionary.
    parameters["cubes"] = AimsCube(plots=("delta_density",))
    # Write control.in file to a string which we can directly access for testing.
    string_output = StringIO()
    write_control(string_output, create_au_bulk_atoms_obj, parameters)
    txt = string_output.getvalue()

    assert contains(r"k_grid\s+2 2 2", txt)
    assert contains(r"k_offset\s+0.250000 0.250000 0.250000", txt)
    assert contains(r"occupation_type\s+gaussian 0.1", txt)
    assert contains(r"output\s+dos 0.0 10.0 101 0.05", txt)
    assert contains(r"output\s+hirshfeld", txt)
    assert contains(r"dos_kgrid_factors\s+21 21 21", txt)
    assert contains(r"vdw_correction_hirshfeld", txt)
    assert contains(r"compute_forces\s+.true.", txt)
    assert contains(r"output_level\s+MD_light", txt)
    assert contains(r"charge\s+0.0", txt)
    assert contains("output cube delta_density", txt)
    assert contains("   cube origin 0 0 0 ", txt)
    assert contains("   cube edge 50 0.1 0.0 0.0 ", txt)
    assert contains("   cube edge 50 0.0 0.1 0.0", txt)
    assert contains("   cube edge 50 0.0 0.0 0.1", txt)


@pytest.mark.parametrize(
    "functional,expected_functional_expression",
    [("PBE", r"xc\s+PBE"), ("LDA", r"xc\s+pw-lda"),
    pytest.param("PBE_06_Fake", None, marks=pytest.mark.xfail)])
def test_control_functional(
        create_au_bulk_atoms_obj, functional: str,
        expected_functional_expression: str):
    """Test that the functional that is set is written to the control.in file."""
    # Copy the global parameters dicitonary to avoid rewriting common
    # parameters. Then assign functional to parameter dictionary.
    parameters = _PARAMETERS_DICT.copy()
    parameters["xc"] = functional
    string_output = StringIO()
    write_control(string_output, create_au_bulk_atoms_obj, parameters)
    txt = string_output.getvalue()
    assert contains(expected_functional_expression, txt)


def test_control_wrong_tier(create_au_bulk_atoms_obj):
    """Test feeding a poorly formatted basis set size ('tier') parameter.
    
    The basis set size (tier) needs to be either None (standard), 0 (minimal),
    1 (tier1), 2 (tier2), etc... A string format will be rejected.
    """
    parameters = _PARAMETERS_DICT.copy()
    parameters["tier"] = "1"
    with pytest.raises(ValueError, match='Given basis tier:'):
        write_control(StringIO(), create_au_bulk_atoms_obj, parameters)

@pytest.mark.parametrize(
    "output_level,tier,expected_basis_set_re",
    [
        ("tight", 0, "#     hydro 4 f 7.4"),
        ("tight", 1,"ionic 6 p auto\n     hydro 4 f 7.4")])
def test_control_tier(
        create_au_bulk_atoms_obj,
        output_level: str, tier: int,
        expected_basis_set_re: str):
    """Test that the correct basis set functions are included.

    For a specific numerical settings (output_level) and basis set size (tier)
    we expect specific basis functions to be included for a species in the
    control.in file. We check that these functions are correctly commented
    for these combinations.

    Args:
        create_au_bulk_atoms_obj: PyTest fixture to create a test Au bulk ase
            Atoms object that we can use to write out the control.in file.
        output_level: The numerical settings (e.g. light, tight, really_tight).
        tier: The basis set size (either None for standard, 0 for minimal, 1 for tier1,
            etc...)
        expected_basis_set_re: Expression we expect to find in the control.in.
            We expect lines to be either commented or uncommented which indicate
            whether a basis set function is included or not in the calcuation.
    """
    parameters = _PARAMETERS_DICT.copy()
    parameters["output_level"] = output_level
    parameters['tier'] = tier
    string_output = StringIO()
    write_control(string_output, create_au_bulk_atoms_obj, parameters)
    txt = string_output.getvalue()
    assert contains(expected_basis_set_re, txt)
