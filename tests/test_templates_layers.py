# Copyright 2018 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Unit tests for the :mod:`pennylane.template.layers` module.
"""
# pylint: disable=protected-access,cell-var-from-loop
import pytest

import logging as log
import pennylane as qml
from pennylane import numpy as np
from pennylane.templates.layers import (CVNeuralNetLayers,
                                        StronglyEntanglingLayers, _strongly_entangling_layer,
                                        RandomLayers, _random_layer)
from pennylane import RX, RY, RZ, CZ, CNOT
log.getLogger('defaults')


class TestCVNeuralNet:
    """Tests for the CVNeuralNet from the pennylane.template module."""

    # Have a fixed number of subsystems in this handcoded test
    @pytest.fixture(scope="class")
    def num_subsystems(self):
        return 4

    @pytest.fixture(scope="class")
    def N(self):
        return 4

    @pytest.fixture(scope="class")
    def depth(self):
        return 2

    @pytest.fixture(scope="class")
    def weights(self):
        return [
                np.array([[ 5.48791879, 6.08552046, 5.46131036, 3.33546468, 1.46227521, 0.0716208 ],
                          [ 3.36869403, 0.63074883, 4.59400392, 5.9040016 , 5.92704296, 2.35455147]]),
                np.array([[ 2.70471535, 2.52804815, 3.28406182, 3.0058243 , 3.48940764, 3.41419504],
                         [ 3.74320919, 4.15936005, 3.20807161, 2.95870535, 0.05574621, 0.42660569]]),
                np.array([[ 4.7808479 , 4.47598146, 3.89357744, 2.67721355],
                         [ 2.73203094, 2.71115444, 1.16794164, 3.32823666]]),
                np.array([[ 0.27344502, 0.68431314, 0.30026443, 0.23128064],
                         [ 0.45945175, 0.53255468, 0.28383751, 0.34263728]]),
                np.array([[ 0.4134863 , 6.17555778, 0.80334114, 2.02400747, 0.44574704, 1.41227118],
                         [ 5.16969442, 3.6890488 , 4.43916808, 3.20808287, 5.21543123, 4.52815349]]),
                np.array([[ 2.47328111, 5.63064513, 2.17059932, 6.1873632 , 0.18052879, 2.20970037],
                         [ 5.44288268, 1.27806129, 1.87574979, 2.98956484, 3.10140853, 3.81814174]]),
                np.array([[ 2.3936353 , 4.80135971, 5.89867895, 2.00867023, 2.71732643, 1.69737575],
                         [ 5.14552399, 3.31578667, 5.90119363, 4.54515204, 1.12316345, 3.89384963]]),
                np.array([[ 5.03318258, 4.01017269, 0.43159284, 3.7928101 ],
                         [ 3.5329307 , 4.79661266, 5.0683084 , 1.87631749]]),
                np.array([[ 1.61159166, 0.1608155 , 0.96535086, 1.60132783],
                         [ 0.36293094, 1.30725604, 0.11578591, 1.5983082 ]]),
                np.array([[ 6.21267547, 3.71076099, 0.34060195, 2.86031556],
                         [ 3.20443756, 6.26536946, 6.18450567, 1.50406923]]),
                np.array([[ 0.1376345 , 0.22541113, 0.14306356, 0.13019402],
                         [ 0.26999146, 0.26256351, 0.14722687, 0.23137066]])
            ]

    def test_cvneuralnet_integration(self, gaussian_device_4modes, weights, depth, N):
        """integration test for the CVNeuralNetLayers template."""

        def circuit(weights):
            CVNeuralNetLayers(*weights, wires=range(N))
            return qml.expval(qml.X(wires=0))

        qnode = qml.QNode(circuit, gaussian_device_4modes)

        # execution test
        qnode(weights)
        queue = qnode.queue

        # Test that gates appear in the right order for each layer:
        # BS-R-S-BS-R-D-K
        for l in range(depth):
            gates = [qml.Beamsplitter, qml.Rotation, qml.Squeezing,
                     qml.Beamsplitter, qml.Rotation, qml.Displacement]

            # count the position of each group of gates in the layer
            num_gates_per_type = [0, 6, 4, 4, 6, 4, 4, 4]
            s = np.cumsum(num_gates_per_type)
            gc = l*sum(num_gates_per_type)+np.array(list(zip(s[:-1], s[1:])))

            # loop through expected gates
            for idx, g in enumerate(gates):
                # loop through where these gates should be in the queue
                for opidx, op in enumerate(queue[gc[idx, 0]:gc[idx, 1]]):
                    # check that op in queue is correct gate
                    assert isinstance(op, g)

                    # test that the parameters are correct
                    res_params = op.parameters

                    if idx == 0:
                        # first BS
                        exp_params = [weights[0][l][opidx], weights[1][l][opidx]]
                    elif idx == 1:
                        # first rot
                        exp_params = [weights[2][l][opidx]]
                    elif idx == 2:
                        # squeezing
                        exp_params = [weights[3][l][opidx], weights[4][l][opidx]]
                    elif idx == 3:
                        # second BS
                        exp_params = [weights[5][l][opidx], weights[6][l][opidx]]
                    elif idx == 4:
                        # second rot
                        exp_params = [weights[7][l][opidx]]
                    elif idx == 5:
                        # displacement
                        exp_params = [weights[8][l][opidx], weights[9][l][opidx]]

                    assert res_params == exp_params

    def test_cvqnn_layers_exception_nlayers(self, gaussian_device_4modes):
        """integration test for the CVNeuralNetLayers method."""

        def circuit(weights):
            CVNeuralNetLayers(*weights, wires=range(4))
            return qml.expval(qml.X(0))

        qnode = qml.QNode(circuit, gaussian_device_4modes)

        wrong_weights = [np.array([1]) if i < 10 else np.array([1, 1]) for i in range(11)]
        with pytest.raises(ValueError) as excinfo:
            qnode(wrong_weights)
        assert excinfo.value.args[0] == "All parameter arrays need to have the same first dimension, from which " \
                                        "the number of layers is inferred; got first dimensions " \
                                        "[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]."


class TestStronglyEntangling:
    """Tests for the StronglyEntanglingLayers method from the pennylane.templates.layers module."""

    def test_integration(self, n_subsystems):
        """integration test for the StronglyEntanglingLayers."""
        np.random.seed(12)
        num_layers = 2
        num_wires = n_subsystems

        dev = qml.device('default.qubit', wires=num_wires)
        weights = np.random.randn(num_layers, num_wires, 3)

        def circuit(weights):
            StronglyEntanglingLayers(weights, wires=range(num_wires))
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)
        qnode(weights)
        queue = qnode.queue

        # Test that gates appear in the right order
        exp_gates = [qml.Rot]*num_wires + [qml.CNOT]*num_wires
        exp_gates *= num_layers
        res_gates = [op for op in queue]

        for op1, op2 in zip(res_gates, exp_gates):
            assert isinstance(op1, op2)

        # test the device parameters
        for l in range(num_layers):
            layer_ops = queue[2*l*num_wires:2*(l+1)*num_wires]

            # check each rotation gate parameter
            for n in range(num_wires):
                res_params = layer_ops[n].parameters
                exp_params = weights[l, n, :]
                assert sum([r == e for r, e in zip(res_params, exp_params)])

    def test_execution(self, tol):
        """Tests the StronglyEntanglingLayers for various parameters."""
        np.random.seed(0)
        outcomes = []

        for num_wires in range(2, 4):
            for num_layers in range(1, 3):

                dev = qml.device('default.qubit', wires=num_wires)
                weights = np.random.randn(num_layers, num_wires, 3)

                @qml.qnode(dev)
                def circuit(weights, x=None):
                    qml.BasisState(x, wires=range(num_wires))
                    StronglyEntanglingLayers(weights, wires=range(num_wires))
                    return qml.expval(qml.PauliZ(0))

                outcomes.append(circuit(weights, x=np.array(np.random.randint(0, 1, num_wires))))

        res = np.array(outcomes)
        expected = np.array([-0.29242496, 0.22129055, 0.07540091, -0.77626557])
        assert np.allclose(res, expected, atol=tol)

    def test_stronglyentangling_layers_exception_subsystems(self):
        """Tests that _strongly_entangling_layer throws exception if n_wires < 2."""
        np.random.seed(12)
        n_rots = 2
        n_wires = 1

        dev = qml.device('default.qubit', wires=n_wires)
        weights = np.random.randn(n_rots)

        def circuit(weights):
            _strongly_entangling_layer(weights=weights, wires=range(n_wires))
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)

        with pytest.raises(ValueError) as excinfo:
            qnode(weights)
        assert excinfo.value.args[0] == "_strongly_entangling_layer requires at least two wires or subsystems to apply " \
                                        "the imprimitive gates."


class TestRandomLayers:
    """Tests for the RandomLayers method from the pennylane.templates module."""

    @pytest.fixture(scope="class",
                    params=[0.2, 0.6])
    def ratio(self, request):
        return request.param

    @pytest.fixture(scope="class",
                    params=[CNOT, CZ])
    def impr(self, request):
        return request.param

    @pytest.fixture(scope="class",
                    params=[[RX], [RY, RZ]])
    def rots(self, request):
        return request.param

    def test_random_layers_deterministic_seed(self, n_layers, tol, seed):
        """Test that RandomLayers() acts deterministically when using fixed seed."""
        n_rots = 1
        n_wires = 2
        dev = qml.device('default.qubit', wires=n_wires)
        weights = np.random.randn(n_layers, n_rots)

        def circuit1(weights):
            RandomLayers(weights=weights, wires=range(n_wires), seed=seed)
            return qml.expval(qml.PauliZ(0))

        def circuit2(weights):
            RandomLayers(weights=weights, wires=range(n_wires), seed=seed)
            return qml.expval(qml.PauliZ(0))

        qnode1 = qml.QNode(circuit1, dev)
        qnode2 = qml.QNode(circuit2, dev)
        assert np.allclose(qnode1(weights), qnode2(weights), atol=tol)

    def test_random_layers_deterministic_default_seed(self, n_layers, tol):
        """Test that RandomLayers() acts deterministically when using default seed."""
        n_rots = 1
        n_wires = 2
        dev = qml.device('default.qubit', wires=n_wires)
        weights = np.random.randn(n_layers, n_rots)

        def circuit1(weights):
            RandomLayers(weights=weights, wires=range(n_wires))
            return qml.expval(qml.PauliZ(0))

        def circuit2(weights):
            RandomLayers(weights=weights, wires=range(n_wires))
            return qml.expval(qml.PauliZ(0))

        qnode1 = qml.QNode(circuit1, dev)
        qnode2 = qml.QNode(circuit2, dev)

        assert np.allclose(qnode1(weights), qnode2(weights), atol=tol)

    def test_random_layers_two_seeds_different(self, n_layers, tol):
        """Test that RandomLayers() does not have the same output for two different seeds."""
        n_rots = 10
        n_wires = 2
        dev = qml.device('default.qubit', wires=n_wires)
        weights = np.random.randn(n_layers, n_rots)

        def circuit1(weights):
            RandomLayers(weights=weights, wires=range(n_wires), seed=0)
            return qml.expval(qml.PauliZ(0))

        def circuit2(weights):
            RandomLayers(weights=weights, wires=range(n_wires), seed=1)
            return qml.expval(qml.PauliZ(0))

        qnode1 = qml.QNode(circuit1, dev)
        qnode2 = qml.QNode(circuit2, dev)

        assert not np.allclose(qnode1(weights), qnode2(weights), atol=tol)

    def test_random_layers_nlayers(self, n_layers):
        """Test that  pennylane.templates.layers.RandomLayers() picks the correct number of gates."""
        np.random.seed(12)
        n_rots = 1
        n_wires = 2
        impr = CNOT
        dev = qml.device('default.qubit', wires=n_wires)
        weights = np.random.randn(n_layers, n_rots)

        def circuit(weights):
            RandomLayers(weights=weights, wires=range(n_wires))
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)
        qnode(weights)
        queue = qnode.queue
        types = [type(q) for q in queue]
        assert len(types) - types.count(impr) == n_layers

    def test_random_layer_imprimitive(self, ratio):
        """Test that  pennylane.templates.layers._random_layer() has the right ratio of imprimitive gates."""
        np.random.seed(12)
        n_rots = 500
        n_wires = 2
        impr = CNOT
        dev = qml.device('default.qubit', wires=n_wires)
        weights = np.random.randn(n_rots)

        def circuit(weights):
            _random_layer(weights=weights, wires=range(n_wires), ratio_imprim=ratio, impr=CNOT)
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)
        qnode(weights)
        queue = qnode.queue
        types = [type(q) for q in queue]
        ratio_impr = types.count(impr) / len(types)
        assert np.isclose(ratio_impr, ratio, atol=0.05)

    def test_random_layer_imprimitive(self, n_subsystems, impr, rots):
        """Test that  pennylane.templates.layers._random_layer() uses the correct types of gates."""
        np.random.seed(12)
        n_rots = 20
        dev = qml.device('default.qubit', wires=n_subsystems)
        weights = np.random.randn(n_rots)

        def circuit(weights):
            _random_layer(weights=weights, wires=range(n_subsystems),
                          imprimitive=impr, rotations=rots)
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)
        qnode(weights)
        queue = qnode.queue
        types = [type(q) for q in queue]
        unique = set(types)
        gates = {impr, *rots}
        assert unique == gates

    def test_random_layer_numgates(self, n_subsystems):
        """Test that  pennylane.templates.layers._random_layer() uses the correct number of gates."""
        np.random.seed(12)
        n_rots = 5
        impr = CNOT
        dev = qml.device('default.qubit', wires=n_subsystems)
        weights = np.random.randn(n_rots)

        def circuit(weights):
            _random_layer(weights=weights, wires=range(n_subsystems), imprimitive=impr)
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)
        qnode(weights)
        queue = qnode.queue
        types = [type(q) for q in queue]
        assert len(types) - types.count(impr) == n_rots

    def test_random_layer_randomwires(self, n_subsystems):
        """Test that  pennylane.templates.layers._random_layer() picks random wires."""
        np.random.seed(12)
        n_rots = 500
        dev = qml.device('default.qubit', wires=n_subsystems)
        weights = np.random.randn(n_rots)

        def circuit(weights):
            _random_layer(weights=weights, wires=range(n_subsystems))
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)
        qnode(weights)
        queue = qnode.queue
        wires = [q._wires for q in queue]
        wires_flat = [item for w in wires for item in w]
        mean_wire = np.mean(wires_flat)
        assert np.isclose(mean_wire, (n_subsystems - 1) / 2, atol=0.05)

    def test_random_layer_imprimitive(self, n_subsystems, tol):
        """Test that pennylane.templates.layers._random_layer() uses the correct weights."""
        np.random.seed(12)
        n_rots = 5
        dev = qml.device('default.qubit', wires=n_subsystems)
        weights = np.random.randn(n_rots)

        def circuit(weights):
            _random_layer(weights=weights, wires=range(n_subsystems))
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)
        qnode(weights)
        queue = qnode.queue
        params = [q.parameters for q in queue]
        params_flat = [item for p in params for item in p]
        assert np.allclose(weights.flatten(), params_flat, atol=tol)

    def test_random_layer_exception_subsystems(self):
        """Tests that pennylane.templates.layers._random_layer() throws exception if n_wires < 2."""
        np.random.seed(12)
        n_rots = 2
        n_wires = 1

        dev = qml.device('default.qubit', wires=n_wires)
        weights = np.random.randn(n_rots)

        def circuit(weights):
            RandomLayers(weights=weights, wires=range(n_wires))
            return qml.expval(qml.PauliZ(0))

        qnode = qml.QNode(circuit, dev)

        with pytest.raises(ValueError) as excinfo:
            qnode(weights)
        assert excinfo.value.args[0] == "_random_layer requires at least two wires or subsystems to apply " \
                                        "the imprimitive gates."
