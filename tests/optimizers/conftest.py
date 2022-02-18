import pytest
import numpy as np
import stko
import stk


def a_molecule():
    return stk.BuildingBlock(smiles='CC')


class PassingOptimizer(stko.Optimizer):

    def optimize(self, mol):
        return a_molecule().with_centroid(np.array(([1, 3, 3])))


class FailingOptimizer(stko.Optimizer):

    def optimize(self, mol):
        raise Exception()


@pytest.fixture
def passing_optimizer():
    return PassingOptimizer()


@pytest.fixture
def failing_optimizer():
    return FailingOptimizer()


@pytest.fixture
def unoptimized_mol():
    return a_molecule()


@pytest.fixture
def optimized_obabel_uff():
    return 0.5915253852361635


@pytest.fixture
def unoptimized_obabel_uff():
    return 30.749185912718534
