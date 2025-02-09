"""
This module defines general-purpose objects, functions and classes.

Functions, classes, etc. defined here should not depend on any other
part of ``stko``. They must be completely self-sufficient.

"""

import rdkit.Chem.AllChem as rdkit
from rdkit.Geometry import Point3D
import numpy as np
import shutil
import os
import subprocess as sp
import gzip
import re
from collections import deque, defaultdict
from glob import iglob
from itertools import chain
from scipy.spatial.distance import euclidean


class WrapperNotInstalledException(Exception):
    ...


# This dictionary gives easy access to the rdkit bond types.
bond_dict = {'1': rdkit.rdchem.BondType.SINGLE,
             'am': rdkit.rdchem.BondType.SINGLE,
             '2': rdkit.rdchem.BondType.DOUBLE,
             '3': rdkit.rdchem.BondType.TRIPLE,
             'ar': rdkit.rdchem.BondType.AROMATIC}

# A dictionary which matches atomic number to elemental symbols.
periodic_table = {
    1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C',
    7: 'N', 8: 'O', 9: 'F', 10: 'Ne', 11: 'Na', 12: 'Mg',
    13: 'Al', 14: 'Si', 15: 'P', 16: 'S', 17: 'Cl',
    18: 'Ar', 19: 'K', 20: 'Ca', 21: 'Sc', 22: 'Ti',
    23: 'V', 24: 'Cr', 25: 'Mn', 26: 'Fe', 27: 'Co',
    28: 'Ni', 29: 'Cu', 30: 'Zn', 31: 'Ga', 32: 'Ge',
    33: 'As', 34: 'Se', 35: 'Br', 36: 'Kr', 37: 'Rb',
    38: 'Sr', 39: 'Y', 40: 'Zr', 41: 'Nb', 42: 'Mo',
    43: 'Tc', 44: 'Ru', 45: 'Rh', 46: 'Pd', 47: 'Ag',
    48: 'Cd', 49: 'In', 50: 'Sn', 51: 'Sb', 52: 'Te',
    53: 'I', 54: 'Xe', 55: 'Cs', 56: 'Ba', 57: 'La',
    58: 'Ce', 59: 'Pr', 60: 'Nd', 61: 'Pm', 62: 'Sm',
    63: 'Eu', 64: 'Gd', 65: 'Tb', 66: 'Dy', 67: 'Ho',
    68: 'Er', 69: 'Tm', 70: 'Yb', 71: 'Lu', 72: 'Hf',
    73: 'Ta', 74: 'W', 75: 'Re', 76: 'Os', 77: 'Ir',
    78: 'Pt', 79: 'Au', 80: 'Hg', 81: 'Tl', 82: 'Pb',
    83: 'Bi', 84: 'Po', 85: 'At', 86: 'Rn', 87: 'Fr',
    88: 'Ra', 89: 'Ac', 90: 'Th', 91: 'Pa', 92: 'U',
    93: 'Np', 94: 'Pu', 95: 'Am', 96: 'Cm', 97: 'Bk',
    98: 'Cf', 99: 'Es', 100: 'Fm', 101: 'Md', 102: 'No',
    103: 'Lr', 104: 'Rf', 105: 'Db', 106: 'Sg', 107: 'Bh',
    108: 'Hs', 109: 'Mt', 110: 'Ds', 111: 'Rg', 112: 'Cn',
    113: 'Uut', 114: 'Fl', 115: 'Uup', 116: 'Lv',
    117: 'Uus', 118: 'Uuo'
}


class MAEExtractor:
    """
    Extracts the lowest energy conformer from a .maegz file.

    Macromodel conformer searches produce -out.maegz files containing
    all of the conformers found during the search and their energies
    and other data.

    Initializing this class with a :class:`.ConstructedMolecule` finds
    the ``-out.maegz`` file of that :class:`.ConstructedMolecule` and
    converts it to a ``.mae`` file. It then creates and additional
    ``.mae`` file holding only the lowest energy conformer found.

    Attributes
    ----------
    maegz_path : :class:`str`
        The path to the ``-out.maegz`` file generated by the macromodel
        conformer search.

    mae_path : :class:`str`
        The path to the ``.mae`` file holding the conformers generated
        by the macromodel conformer search.

    content : :class:`str`
        The content of the ``.mae`` file hodling all the conformers
        from the macromodel conformer search. This holds other data
        such as their energies too.

    energies : :class:`list`
        The :class:`list` has the form

        .. code-block:: python

            energies = [(0, 231.0), (1, 144.4), ...]

        Each :class:`tuple` holds the id and energy of every conformer
        in the ``.mae`` file, respectively.

    min_energy : :class:`float`
        The minimum energy found in the ``.mae`` file.

    path : :class:`str`
        The full path of the ``.mae`` file holding the extracted lowest
        energy conformer.

    """

    def __init__(self, run_name, n=1):
        self.maegz_path = f'{run_name}-out.maegz'
        self.maegz_to_mae()
        self.extract_conformers(n)

    def extract_conformers(self, n):
        """
        Creates ``.mae`` files holding the lowest energy conformers.

        Parameters
        ----------
        n : :class:`int`
            The number of conformers to extract.

        Returns
        -------
        None : :class:`NoneType`

        """

        for i in range(n):
            # Get the id of the lowest energy conformer.
            num = self.lowest_energy_conformers(n)[i][1]
            # Get the structure block corresponding to the lowest
            # energy conformer.
            content = self.content.split("f_m_ct")
            new_mae = "f_m_ct".join([content[0], content[num]])

            # Write the structure block in its own .mae file, named
            # after conformer extracted.
            if n == 1:
                # Write the structure block in its own .mae file, named
                # after conformer extracted.
                new_name = self.mae_path.replace(
                    '.mae',
                    f'EXTRACTED_{num}.mae'
                )
            else:
                new_name = self.mae_path.replace(
                    '.mae',
                    f'EXTRACTED_{num}_conf_{i}.mae'
                )

            with open(new_name, 'w') as mae_file:
                mae_file.write(new_mae)

            if i == 0:
                # Save the path of the newly created file.
                self.path = new_name

    def extract_energy(self, block):
        """
        Extracts the energy value from a ``.mae`` energy data block.

        Parameters
        ----------
        block : :class:`str`
            An ``.mae`` energy data block.

        Returns
        -------
        :class:`float`
            The energy value extracted from `block` or ``None`` if
            one is not found.

        """

        block = block.split(":::")
        for name, value in zip(block[0].split('\n'),
                               block[1].split('\n')):
            if 'r_mmod_Potential_Energy' in name:
                return float(value)

    def lowest_energy_conformers(self, n):
        """
        Returns the id and energy of the lowest energy conformers.

        Parameters
        ----------
        n : :class:`int`
            The number of lowest energy conformers to return.

        Returns
        -------
        :class:`list`
            A :class:`list` of the form

            .. code-block:: python

                returned = [(23, 123.3), (1, 143.89), (12, 150.6), ...]

            Where each :class:`tuple` holds the id and energy of the
            `n` lowest energy conformers, respectively.

        """

        # Open the .mae file holding all the conformers and load its
        # content.
        with open(self.mae_path, 'r') as mae_file:
            self.content = mae_file.read()
            # Split the content across curly braces. This divides the
            # various sections of the .mae file.
            content_split = re.split(r"[{}]", self.content)

        # Go through all the datablocks in the the .mae file. For each
        # energy block extract the energy and store it in the
        # `energies` list. Store the `index`  (conformer id) along with
        # each extracted energy.
        self.energies = []
        prev_block = deque([""], maxlen=1)
        index = 1
        for block in content_split:
            if ("f_m_ct" in prev_block[0] and
               "r_mmod_Potential_Energy" in block):
                energy = self.extract_energy(block)
                self.energies.append((energy, index))
                index += 1

            prev_block.append(block)

        # Selecting the lowest energy n conformers
        confs = sorted(self.energies)[:n]
        # Define the energy of the lowest energy conformer
        self.min_energy = confs[0][0]
        # Return a list with id and energy of the lowest energy
        # conformers.
        return confs

    def maegz_to_mae(self):
        """
        Converts the .maegz file to a .mae file.

        Returns
        -------
        None : :class:`NoneType`

        """

        self.mae_path = self.maegz_path.replace('.maegz', '.mae')
        with gzip.open(self.maegz_path, 'r') as maegz_file:
            with open(self.mae_path, 'wb') as mae_file:
                mae_file.write(maegz_file.read())


def kill_macromodel():
    """
    Kills any applications left open as a result running MacroModel.

    Applications that are typically left open are
    ``jserver-watcher.exe`` and ``jservergo.exe``.

    Returns
    -------
    None : :class:`NoneType`

    """

    try:
        if os.name == 'nt':
            # In Windows, use the ``Taskkill`` command to
            # force a close on the applications.
            sp.run(
                ["Taskkill", "/IM", "jserver-watcher.exe", "/F"],
                stdout=sp.PIPE,
                stderr=sp.PIPE,
            )
            sp.run(
                ["Taskkill", "/IM", "jservergo.exe", "/F"],
                stdout=sp.PIPE,
                stderr=sp.PIPE,
            )

        if os.name == 'posix':
            sp.run(
                ["pkill", "jservergo"],
                stdout=sp.PIPE,
                stderr=sp.PIPE,
            )
            sp.run(
                ["pkill", "jserver-watcher"],
                stdout=sp.PIPE,
                stderr=sp.PIPE,
            )
    except Exception:
        pass


def mol_from_mae_file(mae_path):
    """
    Creates a ``rdkit`` molecule from a ``.mae`` file.

    Parameters
    ----------
    mol2_file : :class:`str`
        The full path of the ``.mae`` file from which an rdkit molecule
        should be instantiated.

    Returns
    -------
    :class:`rdkit.Mol`
        An ``rdkit`` instance of the molecule held in `mae_file`.

    """

    mol = rdkit.EditableMol(rdkit.Mol())
    conf = rdkit.Conformer()

    with open(mae_path, 'r') as mae:
        content = re.split(r'[{}]', mae.read())

    prev_block = deque([''], maxlen=1)
    for block in content:
        if 'm_atom[' in prev_block[0]:
            atom_block = block
        if 'm_bond[' in prev_block[0]:
            bond_block = block
        prev_block.append(block)

    labels, data_block, *_ = atom_block.split(':::')
    labels = [label for label in labels.split('\n')
              if not label.isspace() and label != '']

    data_block = [a.split() for a in data_block.split('\n') if
                  not a.isspace() and a != '']

    for line in data_block:
        line = [word for word in line if word != '"']
        if len(labels) != len(line):
            raise RuntimeError(('Number of labels does'
                                ' not match number of columns'
                                ' in .mae file.'))

        for label, data in zip(labels, line):
            if 'x_coord' in label:
                x = float(data)
            if 'y_coord' in label:
                y = float(data)
            if 'z_coord' in label:
                z = float(data)
            if 'atomic_number' in label:
                atom_num = int(data)

        atom_sym = periodic_table[atom_num]
        atom_coord = Point3D(x, y, z)
        atom_id = mol.AddAtom(rdkit.Atom(atom_sym))
        conf.SetAtomPosition(atom_id, atom_coord)

    labels, data_block, *_ = bond_block.split(':::')
    labels = [label for label in labels.split('\n')
              if not label.isspace() and label != '']
    data_block = [a.split() for a in data_block.split('\n')
                  if not a.isspace() and a != '']

    for line in data_block:
        if len(labels) != len(line):
            raise RuntimeError(('Number of labels does'
                                ' not match number of '
                                'columns in .mae file.'))

        for label, data in zip(labels, line):
            if 'from' in label:
                atom1 = int(data) - 1
            if 'to' in label:
                atom2 = int(data) - 1
            if 'order' in label:
                bond_order = str(int(data))
        mol.AddBond(atom1, atom2, bond_dict[bond_order])

    mol = mol.GetMol()
    mol.AddConformer(conf)
    return mol


def move_generated_macromodel_files(basename, output_dir):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    for filename in iglob(f'{basename}*'):
        # Do not move the output_dir.
        if filename == output_dir:
            continue
        shutil.move(filename, f'{output_dir}/{filename}')


class XTBInvalidSolventError(Exception):
    ...


def is_valid_xtb_solvent(gfn_version, solvent_model, solvent):
    """
    Check if solvent is valid for the given GFN version.

    Parameters
    ----------
    gfn_version : :class:`int`
        GFN parameterization version. Can be: ``0``, ``1`` or ``2``.

    solvent_model : class:`str`
        Solvent model being used [1]_.

    solvent : :class:`str`
        Solvent being tested [1]_.

    Returns
    -------
    :class:`bool`
        ``True`` if solvent is valid.

    References
    ----------
    .. [1] https://xtb-docs.readthedocs.io/en/latest/gbsa.html

    """

    if gfn_version == 0:
        return False
    elif gfn_version == 1 and solvent_model == 'gbsa':
        valid_solvents = {
            'acetone', 'acetonitrile', 'benzene',
            'CH2Cl2'.lower(), 'CHCl3'.lower(), 'CS2'.lower(),
            'DMSO'.lower(), 'ether', 'H2O'.lower(),
            'methanol', 'THF'.lower(), 'toluene', 'water',
        }
    elif gfn_version == 1 and solvent_model == 'alpb':
        valid_solvents = {
            'acetone', 'acetonitrile', 'aniline', 'benzaldehyde',
            'benzene', 'CH2Cl2'.lower(), 'CHCl3'.lower(),
            'CS2'.lower(), 'dioxane', 'DMF'.lower(), 'DMSO'.lower(),
            'ether', 'ethylacetate', 'furane',
            'hexandecane', 'hexane', 'H2O'.lower(), 'nitromethane',
            'octanol', 'octanol (wet)', 'phenol', 'THF'.lower(),
            'toluene', 'water',
        }
    elif gfn_version == 2 and solvent_model == 'gbsa':
        valid_solvents = {
            'acetone', 'acetonitrile',
            'benzene', 'CH2Cl2'.lower(), 'CHCl3'.lower(),
            'CS2'.lower(), 'DMSO'.lower(),
            'ether', 'hexane', 'methanol', 'H2O'.lower(),
            'THF'.lower(), 'toluene', 'water',
        }
    elif gfn_version == 2 and solvent_model == 'alpb':
        valid_solvents = {
            'acetone', 'acetonitrile', 'aniline', 'benzaldehyde',
            'benzene', 'CH2Cl2'.lower(), 'CHCl3'.lower(),
            'CS2'.lower(), 'dioxane', 'DMF'.lower(), 'DMSO'.lower(),
            'ether', 'ethylacetate', 'furane',
            'hexandecane', 'hexane', 'H2O'.lower(), 'nitromethane',
            'octanol', 'octanol (wet)', 'phenol', 'THF'.lower(),
            'toluene', 'water',
        }
    return solvent in valid_solvents


def get_plane_normal(points):
    centroid = points.sum(axis=0) / len(points)
    return np.linalg.svd(points - centroid)[-1][2, :]


def has_h_atom(bond):
    """
    Check if a bond has a H atom.

    Parameters
    ----------
    bond : :class:`stk.Bond`
        Bond to test if it has a H atom.

    Returns
    -------
    :class:`bool`
        Returns `True` if bond has H atom.

    """

    if bond.get_atom1().get_atomic_number() == 1:
        return True
    if bond.get_atom2().get_atomic_number() == 1:
        return True

    return False


def has_metal_atom(bond, metal_atoms):
    """
    Check if a bond has a metal atom.

    Parameters
    ----------
    bond : :class:`stk.Bond`
        Bond to test if it has a metal atom.

    metal_atoms : :class:`.list` of :class:`stk.Atom`
        List of metal atoms.

    Returns
    -------
    :class:`bool`
        Returns `True` if bond has metal atom.

    """

    if bond.get_atom1() in metal_atoms:
        return True
    if bond.get_atom2() in metal_atoms:
        return True

    return False


def metal_atomic_numbers():

    return chain(range(21, 31), range(39, 49), range(72, 81))


def get_metal_atoms(mol):
    """
    Return a list of metal atoms in molecule.

    """

    metal_atoms = []
    for atom in mol.get_atoms():
        if atom.get_atomic_number() in metal_atomic_numbers():
            metal_atoms.append(atom)

    return metal_atoms


def get_metal_bonds(mol, metal_atoms):
    """
    Return a list of bonds in molecule that contain metal atoms.

    """

    metal_bonds = []
    ids_to_metals = []
    for bond in mol.get_bonds():
        if bond.get_atom1() in metal_atoms:
            metal_bonds.append(bond)
            ids_to_metals.append(bond.get_atom2().get_id())
        elif bond.get_atom2() in metal_atoms:
            metal_bonds.append(bond)
            ids_to_metals.append(bond.get_atom1().get_id())

    return metal_bonds, ids_to_metals


def to_rdkit_mol_without_metals(mol, metal_atoms, metal_bonds):
    """
    Create :class:`rdkit.Mol` with metals replaced by H atoms.

    Parameters
    ----------
    mol : :class:`.Molecule`
        The molecule to be optimized.

    metal_atoms : :class:`.list` of :class:`stk.Atom`
        List of metal atoms.

    metal_bonds : :class:`.list` of :class:`stk.Bond`
        List of bonds including metal atoms.

    Returns
    -------
    edit_mol : :class:`rdkit.Mol`
        RDKit molecule with metal atoms replaced with H atoms.

    """
    edit_mol = rdkit.EditableMol(rdkit.Mol())
    for atom in mol.get_atoms():
        if atom in metal_atoms:
            # In place of metals, add H's that will be constrained.
            # This allows the atom ids to not be changed.
            rdkit_atom = rdkit.Atom(1)
            rdkit_atom.SetFormalCharge(0)
        else:
            rdkit_atom = rdkit.Atom(atom.get_atomic_number())
            rdkit_atom.SetFormalCharge(atom.get_charge())
        edit_mol.AddAtom(rdkit_atom)

    for bond in mol.get_bonds():
        if bond in metal_bonds:
            # Do not add bonds to metal atoms (replaced with H's).
            continue
        edit_mol.AddBond(
            beginAtomIdx=bond.get_atom1().get_id(),
            endAtomIdx=bond.get_atom2().get_id(),
            order=rdkit.BondType(bond.get_order())
        )

    edit_mol = edit_mol.GetMol()
    rdkit_conf = rdkit.Conformer(mol.get_num_atoms())
    for atom_id, atom_coord in enumerate(mol.get_position_matrix()):
        rdkit_conf.SetAtomPosition(atom_id, atom_coord)
        edit_mol.GetAtomWithIdx(atom_id).SetNoImplicit(True)
    edit_mol.AddConformer(rdkit_conf)

    return edit_mol


def get_atom_distance(position_matrix, atom1_id, atom2_id):
    """
    Return the distance between two atoms.

    """

    distance = euclidean(
        u=position_matrix[atom1_id],
        v=position_matrix[atom2_id]
    )

    return float(distance)


def get_long_bond_ids(mol, reorder=False):
    """
    Return tuple of long bond ids in a ConstructedMolecule.

    """

    long_bond_ids = []
    for bond_infos in mol.get_bond_infos():
        if bond_infos.get_building_block() is None:
            if reorder:
                ba1 = bond_infos.get_bond().get_atom1().get_id()
                ba2 = bond_infos.get_bond().get_atom2().get_id()
                if ba1 < ba2:
                    ids = (
                        bond_infos.get_bond().get_atom1().get_id(),
                        bond_infos.get_bond().get_atom2().get_id(),
                    )
                else:
                    ids = (
                        bond_infos.get_bond().get_atom2().get_id(),
                        bond_infos.get_bond().get_atom1().get_id(),
                    )
            else:
                ids = (
                    bond_infos.get_bond().get_atom1().get_id(),
                    bond_infos.get_bond().get_atom2().get_id(),
                )
            long_bond_ids.append(ids)

    return tuple(long_bond_ids)


def calculate_dihedral(pt1, pt2, pt3, pt4):
    """
    Calculate the dihedral between four points in degrees.

    Uses Praxeolitic formula --> 1 sqrt, 1 cross product
    Output in range (-180 to 180).

    From: https://stackoverflow.com/questions/20305272/
    dihedral-torsion-angle-from-four-points-in-cartesian-
    coordinates-in-python
    (new_dihedral(p))

    """

    p0 = np.asarray(pt1)
    p1 = np.asarray(pt2)
    p2 = np.asarray(pt3)
    p3 = np.asarray(pt4)

    b0 = -1.0 * (p1 - p0)
    b1 = p2 - p1
    b2 = p3 - p2

    # normalize b1 so that it does not influence magnitude of vector
    # rejections that come next
    b1 /= np.linalg.norm(b1)

    # vector rejections
    # v = projection of b0 onto plane perpendicular to b1
    #   = b0 minus component that aligns with b1
    # w = projection of b2 onto plane perpendicular to b1
    #   = b2 minus component that aligns with b1
    v = b0 - np.dot(b0, b1) * b1
    w = b2 - np.dot(b2, b1) * b1

    # angle between v and w in a plane is the torsion angle
    # v and w may not be normalized but that's fine since tan is y/x
    x = np.dot(v, w)
    y = np.dot(np.cross(b1, v), w)
    return np.degrees(np.arctan2(y, x))


def vector_angle(vector1, vector2):
    """
    Returns the angle between two vectors in radians.
    Parameters
    ----------
    vector1 : :class:`numpy.ndarray`
        The first vector.
    vector2 : :class:`numpy.ndarray`
        The second vector.
    Returns
    -------
    :class:`float`
        The angle between `vector1` and `vector2` in radians.
    """

    if np.all(np.equal(vector1, vector2)):
        return 0.

    numerator = np.dot(vector1, vector2)
    denominator = np.linalg.norm(vector1) * np.linalg.norm(vector2)
    # This if statement prevents returns of NaN due to floating point
    # inaccuracy.
    term = numerator/denominator
    if term >= 1.:
        return 0.0
    if term <= -1.:
        return np.pi
    return np.arccos(term)


def calculate_angle(pt1, pt2, pt3):
    """
    Calculate the angle between three points in degrees.

    """

    v1 = pt1 - pt2
    v2 = pt3 - pt2
    return np.degrees(vector_angle(v1, v2))


def get_torsion_info_angles(mol, torsion_info):
    """
    Get the angles for torsion_info in mol.

    The first angle returned is torsion angle in the
    :class:`stk.ConstructedMolecule`.
    The second angle returned is torsion angle in the
    :class:`stk.BuildingBlock`.
    Both angles are in degrees.

    A :class:`stko.MatchedTorsionCalculator` should yield torsions
    such that the two angles returned are the same.

    Parameters
    ----------
    mol : :class:`.ConstructedMolecule`
        The :class:`.ConstructedMolecule` for which angles are
        computed.

    torsion_info : TorsionInfo
        Specifies the torsion for which angles will be computed.

    Returns
    -------
    angle : :class:`float`, bb_angle : :class:`float`

    """

    torsion = torsion_info.get_torsion()
    angle = calculate_dihedral(
        pt1=tuple(
            mol.get_atomic_positions(
                torsion.get_atom_ids()[0]
            )
        )[0],
        pt2=tuple(
            mol.get_atomic_positions(
                torsion.get_atom_ids()[1]
            )
        )[0],
        pt3=tuple(
            mol.get_atomic_positions(
                torsion.get_atom_ids()[2]
            )
        )[0],
        pt4=tuple(
            mol.get_atomic_positions(
                torsion.get_atom_ids()[3]
            )
        )[0],
    )
    bb_torsion = torsion_info.get_building_block_torsion()
    if bb_torsion is None:
        bb_angle = None
    else:
        bb_angle = calculate_dihedral(
            pt1=tuple(
                torsion_info.get_building_block().get_atomic_positions(
                    bb_torsion.get_atom_ids()[0]
                )
            )[0],
            pt2=tuple(
                torsion_info.get_building_block().get_atomic_positions(
                    bb_torsion.get_atom_ids()[1]
                )
            )[0],
            pt3=tuple(
                torsion_info.get_building_block().get_atomic_positions(
                    bb_torsion.get_atom_ids()[2]
                )
            )[0],
            pt4=tuple(
                torsion_info.get_building_block().get_atomic_positions(
                    bb_torsion.get_atom_ids()[3]
                )
            )[0],
        )
    return angle, bb_angle


def get_atom_maps(mol):
    """
    Get atom maps from building blocks to constructude molecule.

    Returns a dictionary of dictionaries from atom id (in building
    block) to constructed molecule atom, indexed by building block id.

    Parameters
    ----------
    mol : :class:`.ConstructedMolecule`
        The :class:`.ConstructedMolecule` for which atom maps are
        desired.

    """
    atom_maps = defaultdict(dict)
    for atom_info in mol.get_atom_infos():
        bb_atom_id = atom_info.get_building_block_atom().get_id()
        atom_maps[atom_info.get_building_block_id()][
            bb_atom_id
        ] = atom_info.get_atom()
    return atom_maps


def is_inequivalent_atom(atom1, atom2):
    if atom1.__class__ is not atom2.__class__:
        return True
    if atom1.get_id() != atom2.get_id():
        return True
    if atom1.get_charge() != atom2.get_charge():
        return True
    if atom1.get_atomic_number() != atom2.get_atomic_number():
        return True
