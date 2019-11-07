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
Integration tests for templates, including integration of passing outputs of initialization functions
in :mod:`pennylane.init`, and running templates in larger circuits.
"""
# pylint: disable=protected-access,cell-var-from-loop
import pytest
import torch
import tensorflow as tf
import numpy as np
import pennylane as qml
from pennylane.templates.layers import Interferometer
from pennylane.templates.layers import (CVNeuralNetLayers, CVNeuralNetLayer,
                                        StronglyEntanglingLayers, StronglyEntanglingLayer,
                                        RandomLayers, RandomLayer)
from pennylane.templates.embeddings import (AmplitudeEmbedding, BasisEmbedding,
                                            AngleEmbedding, SqueezingEmbedding,
                                            DisplacementEmbedding)
from pennylane.init import (strong_ent_layers_uniform, strong_ent_layer_uniform,
                            strong_ent_layers_normal, strong_ent_layer_normal,
                            random_layers_uniform, random_layer_uniform,
                            random_layers_normal, random_layer_normal,
                            cvqnn_layers_uniform, cvqnn_layer_uniform,
                            cvqnn_layers_normal, cvqnn_layer_normal)

# Prepate automatic tests for templates with standard signature (one weight input)
layer_weights_vars = "template, weights"
layer_weights = [(StronglyEntanglingLayers,
                  [[[1.50820225, 4.24049172, 5.58068076], [3.72927363, 5.4538957, 1.21793098]],
                   [[5.25049813, 1.11059904, 0.52967773], [4.9789569, 1.42562158, 2.49977512]]]
                  ),
                 (RandomLayers,
                  [[0.53479316, 5.88709314], [2.21352321, 4.28468607]]
                  )]

layer_init_vars = "template, init"
layer_init = [(StronglyEntanglingLayers, strong_ent_layers_uniform),
              (StronglyEntanglingLayers, strong_ent_layers_normal),
              (RandomLayers, random_layers_uniform),
              (RandomLayers, random_layers_normal)
             ]

emb_inputs_vars = "template, features"
embeddings_inputs = [(AmplitudeEmbedding,
                      [1 / 2, 1 / 2, 1 / 2, 1 / 2]),
                     (BasisEmbedding,
                      [1, 0]),
                     (AngleEmbedding,
                      [1., 2.])]
embeddings_inputs_cv = [(DisplacementEmbedding,
                         [1., 2.]),
                        (SqueezingEmbedding,
                         [1., 2.])]


class TestParameterIntegration:
    """Tests integration with the parameter initialization functions from pennylane.init"""

    @pytest.mark.parametrize(layer_init_vars, layer_init)
    def test_init_integration_standard_layers(self, template, init, qubit_device, n_subsystems, n_layers):
        """Checks that parameters generated by methods from pennylane.init integrate
        with StronglyEntanglingLayers()."""

        p = init(n_layers=n_layers, n_wires=n_subsystems)

        @qml.qnode(qubit_device)
        def circuit(weights):
            template(*weights, wires=range(n_subsystems))
            return qml.expval(qml.Identity(0))

        circuit(weights=p)

    @pytest.mark.parametrize('init', [cvqnn_layers_uniform, cvqnn_layers_normal])
    def test_init_integration_cvqnn_layers(self, init, gaussian_device, n_subsystems, n_layers):
        """Checks that pennylane.init.cvqnn_layers_uniform() integrates
        with CVNeuralNetLayers()."""

        p = init(n_layers=n_layers, n_wires=n_subsystems)

        @qml.qnode(gaussian_device)
        def circuit(weights):
            CVNeuralNetLayers(*weights, wires=range(n_subsystems))
            return qml.expval(qml.Identity(0))

        circuit(weights=p)


class TestCircuitIntegration:
    """Tests the integration of templates into circuits with operations before and after. """

    @pytest.mark.parametrize(layer_weights_vars, layer_weights)
    def test_circuit_integration_standard_layers(self, template, weights):
        """Checks that a range of standard layer can be used with other operations
        in a circuit."""

        p = np.array(weights)
        dev = qml.device('default.qubit', wires=2)

        @qml.qnode(dev)
        def circuit(weights):
            qml.PauliX(wires=0)
            template(weights, wires=range(2))
            template(weights, wires=range(2))
            qml.PauliX(wires=1)
            return [qml.sample(qml.Identity(0)), qml.expval(qml.PauliX(1))]

        circuit(weights=p)

    @pytest.mark.parametrize(emb_inputs_vars, embeddings_inputs)
    def test_circuit_integration_standard_embedding(self, template, features):
        """Checks that standard embeddings can be used with other operations
        in a circuit."""

        features = np.array(features)

        dev = qml.device('default.qubit', wires=2)

        @qml.qnode(dev)
        def circuit(feats=None):
            qml.PauliX(wires=0)
            template(features=feats, wires=range(2))
            template(features=feats, wires=range(2))
            qml.PauliX(wires=1)
            return [qml.sample(qml.Identity(0)), qml.expval(qml.PauliX(1))]

        circuit(feats=features)

    @pytest.mark.parametrize(emb_inputs_vars, embeddings_inputs_cv)
    def test_circuit_integration_standard_cv_embedding(self, gaussian_device_2_wires, template, features):
        """Checks that standard continuous-variable embeddings can be used with other operations
        in a circuit."""

        f = np.array(features)

        @qml.qnode(gaussian_device_2_wires)
        def circuit(feats=None):
            qml.Displacement(1., 1., wires=0)
            template(features=feats, wires=range(2))
            template(features=feats, wires=range(2))
            qml.Displacement(1., 1., wires=1)
            return [qml.expval(qml.Identity(0)), qml.expval(qml.X(1))]

        circuit(feats=f)

    def test_circuit_integration_cvqnn_layers(self, gaussian_device_2_wires):
        """Checks that StronglyEntanglingLayers() can be used with other operations
        in a circuit."""

        p = [np.array([[2.33312851], [1.20670562]]),
             np.array([[3.49488327], [2.01683706]]),
             np.array([[0.9868003, 1.58798724], [5.06301407, 4.83852562]]),
             np.array([[0.21358641,  0.120304], [-0.00724019, 0.01996744]]),
             np.array([[4.62040076, 6.08773452], [6.09056998, 6.22395862]]),
             np.array([[4.10336783], [1.70001985]]),
             np.array([[4.74112903], [5.31462729]]),
             np.array([[0.89758198, 0.41604762], [1.09680782, 3.08223802]]),
             np.array([[-0.0807571, -0.00908855], [0.06051908, -0.1667079]]),
             np.array([[1.87210909, 3.59695024], [1.42759279, 3.84330071]]),
             np.array([[0.00389139,  0.05125553], [-0.12120044,  0.03111934]])
             ]

        @qml.qnode(gaussian_device_2_wires)
        def circuit(weights):
            qml.Displacement(1., 1., wires=0)
            CVNeuralNetLayers(*weights, wires=range(2))
            CVNeuralNetLayers(*weights, wires=range(2))
            qml.Displacement(1., 1., wires=1)
            return [qml.expval(qml.Identity(0)), qml.expval(qml.X(1))]

        circuit(weights=p)

    def test_circuit_integration_interferometer(self, gaussian_device_2_wires):
        """Checks that pennnylane.templates.Interferometer() can be used with other operations
        in a circuit."""

        p = [np.array([2.33312851]),
             np.array([3.49488327]),
             np.array([0.9868003, 1.58798724])
             ]

        @qml.qnode(gaussian_device_2_wires)
        def circuit(weights):
            qml.Displacement(1., 1., wires=0)
            Interferometer(*weights, wires=range(2))
            Interferometer(*weights, wires=range(2))
            qml.Displacement(1., 1., wires=1)
            return [qml.expval(qml.Identity(0)), qml.expval(qml.X(1))]

        circuit(weights=p)


class TestQNodeIntegration:
    """Tests the integration of templates with different ways to pass parameters to a QNode."""

    # @pytest.mark.parametrize(layer_inputs, layers)
    # def test_qnode_integration_standard_qubit_layers(self, template, weights):
    #     """Checks that a range of standard layer can be used with other operations
    #     in a circuit."""
    #
    #     p = np.array(weights)
    #     dev = qml.device('default.qubit', wires=2)
    #
    #     @qml.qnode(dev)
    #     def circuit(weights):
    #         qml.PauliX(wires=0)
    #         template(weights, wires=range(2))
    #         template(weights, wires=range(2))
    #         qml.PauliX(wires=1)
    #         return [qml.sample(qml.Identity(0)), qml.expval(qml.PauliX(1))]
    #
    #     circuit(weights=p)
    #
    # @pytest.mark.parametrize(standard_qubit_emb_names, standard_qubit_embeddings)
    # def test_qnode_integration_standard_qubit_embedding(self, template, features, weights):
    #     """Checks that standard embeddings can be used with other operations
    #     in a circuit."""
    #
    #     features = np.array(features)
    #
    #     dev = qml.device('default.qubit', wires=2)
    #
    #     @qml.qnode(dev)
    #     def circuit(feats=None):
    #         qml.PauliX(wires=0)
    #         template(features=feats, wires=range(2))
    #         template(features=feats, wires=range(2))
    #         qml.PauliX(wires=1)
    #         return [qml.sample(qml.Identity(0)), qml.expval(qml.PauliX(1))]
    #
    #     circuit(feats=features)
    #
    # @pytest.mark.parametrize(standard_cv_emb_names, standard_cv_embeddings)
    # def test_qnode_integration_standard_cv_embedding(self, gaussian_device_2_wires, template, features, weights):
    #     """Checks that standard continuous-variable embeddings can be used with other operations
    #     in a circuit."""
    #
    #     f = np.array(features)
    #
    #     @qml.qnode(gaussian_device_2_wires)
    #     def circuit(feats=None):
    #         qml.Displacement(1., 1., wires=0)
    #         template(features=feats, wires=range(2))
    #         template(features=feats, wires=range(2))
    #         qml.Displacement(1., 1., wires=1)
    #         return [qml.expval(qml.Identity(0)), qml.expval(qml.X(1))]
    #
    #     circuit(feats=f)
    #
    # def test_qnode_integration_cvqnn_layers(self, gaussian_device_2_wires):
    #     """Checks that StronglyEntanglingLayers() can be used with other operations
    #     in a circuit."""
    #
    #     p = [np.array([[2.33312851], [1.20670562]]),
    #          np.array([[3.49488327], [2.01683706]]),
    #          np.array([[0.9868003, 1.58798724], [5.06301407, 4.83852562]]),
    #          np.array([[0.21358641, 0.120304], [-0.00724019, 0.01996744]]),
    #          np.array([[4.62040076, 6.08773452], [6.09056998, 6.22395862]]),
    #          np.array([[4.10336783], [1.70001985]]),
    #          np.array([[4.74112903], [5.31462729]]),
    #          np.array([[0.89758198, 0.41604762], [1.09680782, 3.08223802]]),
    #          np.array([[-0.0807571, -0.00908855], [0.06051908, -0.1667079]]),
    #          np.array([[1.87210909, 3.59695024], [1.42759279, 3.84330071]]),
    #          np.array([[0.00389139, 0.05125553], [-0.12120044, 0.03111934]])
    #          ]
    #
    #     @qml.qnode(gaussian_device_2_wires)
    #     def circuit(weights):
    #         qml.Displacement(1., 1., wires=0)
    #         CVNeuralNetLayers(*weights, wires=range(2))
    #         CVNeuralNetLayers(*weights, wires=range(2))
    #         qml.Displacement(1., 1., wires=1)
    #         return [qml.expval(qml.Identity(0)), qml.expval(qml.X(1))]
    #
    #     circuit(weights=p)
    #
    # def test_qnode_integration_interferometer(self, gaussian_device_2_wires):
    #     """Checks that pennnylane.templates.Interferometer() can be used with other operations
    #     in a circuit."""
    #
    #     p = [np.array([2.33312851]),
    #          np.array([3.49488327]),
    #          np.array([0.9868003, 1.58798724])
    #          ]
    #
    #     @qml.qnode(gaussian_device_2_wires)
    #     def circuit(weights):
    #         qml.Displacement(1., 1., wires=0)
    #         Interferometer(*weights, wires=range(2))
    #         Interferometer(*weights, wires=range(2))
    #         qml.Displacement(1., 1., wires=1)
    #         return [qml.expval(qml.Identity(0)), qml.expval(qml.X(1))]
    #
    #     circuit(weights=p)


class TestInterfaceIntegration:
    """Tests the integration of templates with interfaces."""

    @pytest.mark.parametrize(layer_weights_vars, layer_weights)
    def test_interface_integration_standard_layers_torch(self, template, weights):
        """Checks that pennylane.templates.layers.StronglyEntanglingLayers() can be used with the
        PyTorch interface."""

        p = torch.tensor(weights)
        dev = qml.device('default.qubit', wires=2)

        @qml.qnode(dev, interface='torch')
        def circuit(weights):
            template(weights, wires=range(2))
            return qml.expval(qml.Identity(0))

        circuit(weights=p)

    @pytest.mark.parametrize(layer_weights_vars, layer_weights)
    def test_interface_integration_standard_layers_tf(self, template, weights):
        """Checks that pennylane.templates.layers.StronglyEntanglingLayers() can be used with the
        TensorFlow interface."""

        p = tf.Variable([[[1.50820225, 4.24049172, 5.58068076], [3.72927363, 5.4538957, 1.21793098]],
                         [[5.25049813, 1.11059904, 0.52967773], [4.9789569, 1.42562158, 2.49977512]]])
        dev = qml.device('default.qubit', wires=2)

        @qml.qnode(dev, interface='tf')
        def circuit(weights):
            StronglyEntanglingLayers(weights, wires=range(2))
            return qml.expval(qml.Identity(0))

        circuit(weights=p)

    def test_interface_integration_cvqnn_layers_torch(self, gaussian_device_2_wires):
        """Checks that pennylane.templates.layers.StronglyEntanglingLayers() can be used with the
        PyTorch interface."""

        p = [torch.tensor([[2.33312851], [1.20670562]]),
             torch.tensor([[3.49488327], [2.01683706]]),
             torch.tensor([[0.9868003, 1.58798724], [5.06301407, 4.83852562]]),
             torch.tensor([[0.21358641, 0.120304], [-0.00724019, 0.01996744]]),
             torch.tensor([[4.62040076, 6.08773452], [6.09056998, 6.22395862]]),
             torch.tensor([[4.10336783], [1.70001985]]),
             torch.tensor([[4.74112903], [5.31462729]]),
             torch.tensor([[0.89758198, 0.41604762], [1.09680782, 3.08223802]]),
             torch.tensor([[-0.0807571, -0.00908855], [0.06051908, -0.1667079]]),
             torch.tensor([[1.87210909, 3.59695024], [1.42759279, 3.84330071]]),
             torch.tensor([[0.00389139, 0.05125553], [-0.12120044, 0.03111934]])
             ]

        @qml.qnode(gaussian_device_2_wires, interface='torch')
        def circuit(w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, w11):
            CVNeuralNetLayers(w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, w11, wires=range(2))
            return qml.expval(qml.Identity(0))

        circuit(*p)

    def test_interface_integration_cvqnn_layers_tf(self, gaussian_device_2_wires):
        """Checks that pennylane.templates.layers.StronglyEntanglingLayers() can be used with the
        TensorFlow interface."""

        p = [tf.Variable([[2.33312851], [1.20670562]]),
             tf.Variable([[3.49488327], [2.01683706]]),
             tf.Variable([[0.9868003, 1.58798724], [5.06301407, 4.83852562]]),
             tf.Variable([[0.21358641, 0.120304], [-0.00724019, 0.01996744]]),
             tf.Variable([[4.62040076, 6.08773452], [6.09056998, 6.22395862]]),
             tf.Variable([[4.10336783], [1.70001985]]),
             tf.Variable([[4.74112903], [5.31462729]]),
             tf.Variable([[0.89758198, 0.41604762], [1.09680782, 3.08223802]]),
             tf.Variable([[-0.0807571, -0.00908855], [0.06051908, -0.1667079]]),
             tf.Variable([[1.87210909, 3.59695024], [1.42759279, 3.84330071]]),
             tf.Variable([[0.00389139, 0.05125553], [-0.12120044, 0.03111934]])
             ]

        @qml.qnode(gaussian_device_2_wires, interface='tf')
        def circuit(w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, w11):
            CVNeuralNetLayers(w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, w11, wires=range(2))
            return qml.expval(qml.Identity(0))

        circuit(*p)

    def test_interface_integration_interferometer_torch(self, gaussian_device_2_wires):
        """Checks that pennnylane.templates.Interferometer() can be used with the
        PyTorch interface."""

        p = [torch.tensor([2.33312851]),
             torch.tensor([3.49488327]),
             torch.tensor([0.9868003, 1.58798724])
             ]

        @qml.qnode(gaussian_device_2_wires, interface='torch')
        def circuit(w1, w2, w3):
            Interferometer(w1, w2, w3, wires=range(2))
            return qml.expval(qml.Identity(0))

        circuit(*p)

    def test_interface_integration_interferometer_tf(self, gaussian_device_2_wires):
        """Checks that pennnylane.templates.Interferometer() can be used with the
        TensorFlow interface."""

        p = [tf.Variable([2.33312851]),
             tf.Variable([3.49488327]),
             tf.Variable([0.9868003, 1.58798724])
             ]

        @qml.qnode(gaussian_device_2_wires, interface='tf')
        def circuit(w1, w2, w3):
            Interferometer(w1, w2, w3, wires=range(2))
            return qml.expval(qml.Identity(0))

        circuit(*p)

    @pytest.mark.parametrize(emb_inputs_vars, embeddings_inputs)
    def test_interface_integration_standard_embedding_torch(self, template, features):
        """Checks that standard embeddings can be used with the
            PyTorch interface."""

        f = torch.tensor(features)
        dev = qml.device('default.qubit', wires=2)

        @qml.qnode(dev, interface='torch')
        def circuit(feats=None):
            template(features=feats, wires=range(2))
            return qml.expval(qml.Identity(0))

        circuit(feats=f)

    # @pytest.mark.parametrize(standard_qubit_emb_names, standard_qubit_embeddings)
    # def test_interface_integration_standard_embedding_tf(self, template, features, weights):
    #     """Checks that standard embeddings can be used with the
    #         Tensorflow interface."""
    #
    #     f = tf.Variable(features)
    #     dev = qml.device('default.qubit', wires=2)
    #
    #     @qml.qnode(dev, interface='tf')
    #     def circuit(f=None):
    #         template(features=f, wires=range(2), normalize=True)
    #         return qml.expval(qml.Identity(0))
    #
    #     circuit(f=f)

    @pytest.mark.parametrize(emb_inputs_vars, embeddings_inputs_cv)
    def test_interface_integration_standard_cv_embedding_torch(self, gaussian_device_2_wires, template, features):
        """Checks that standard cv embeddings can be used with the
           PyTorch interface."""

        f = torch.tensor(features)

        @qml.qnode(gaussian_device_2_wires, interface='torch')
        def circuit(feats=None):
            template(features=feats, wires=range(2))
            return qml.expval(qml.Identity(0))

        circuit(feats=f)

    # @pytest.mark.parametrize(emb_inputs_vars, embeddings_inputs)
    # def test_interface_integration_squeezing_embedding_tf(self, gaussian_device_2_wires, template, features, weights):
    #     """Checks that standard cv embeddings can be used with the
    #        TensorFlow interface."""
    #
    #     f = tf.Variable(features)
    #
    #     @qml.qnode(gaussian_device_2_wires, interface='tf')
    #     def circuit(feats=None):
    #         template(features=feats, wires=range(2))
    #         return qml.expval(qml.Identity(0))
    #
    #     circuit(feats=f)
    #
    #
