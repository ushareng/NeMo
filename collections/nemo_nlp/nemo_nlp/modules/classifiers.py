__all__ = ['TokenClassifier',
           'SequenceClassifier',
           'JointIntentSlotClassifier']

import torch
import torch.nn as nn

from nemo.backends.pytorch.common import MultiLayerPerceptron
from nemo.backends.pytorch.nm import TrainableNM, LossNM
from nemo.core.neural_types import *

from ..transformer.utils import transformer_weights_init


class TokenClassifier(TrainableNM):
    @staticmethod
    def create_ports():
        input_ports = {
            "hidden_states": NeuralType({
                0: AxisType(BatchTag),
                1: AxisType(TimeTag),
                2: AxisType(ChannelTag)
            })
        }

        output_ports = {
            "logits": NeuralType({
                0: AxisType(BatchTag),
                1: AxisType(TimeTag),
                2: AxisType(ChannelTag)
            })
        }
        return input_ports, output_ports

    def __init__(self,
                 hidden_size,
                 num_classes,
                 num_layers=2,
                 activation='relu',
                 log_softmax=True,
                 dropout=0.0,
                 use_transformer_pretrained=True):
        super().__init__()

        self.mlp = MultiLayerPerceptron(hidden_size,
                                        num_classes,
                                        self._device,
                                        num_layers,
                                        activation,
                                        log_softmax)
        self.dropout = nn.Dropout(dropout)
        if use_transformer_pretrained:
            self.apply(
                lambda module: transformer_weights_init(module, xavier=False))
        # self.to(self._device) # sometimes this is necessary

    def forward(self, hidden_states):
        hidden_states = self.dropout(hidden_states)
        logits = self.mlp(hidden_states)
        return logits


class SequenceClassifier(TrainableNM):
    """
    The softmax classifier for sequence classifier task.
    Some examples of this task would be sentiment analysis,
    sentence classification, etc.

    Args:
        hidden_size (int): the size of the hidden state for the dense layer
        num_classes (int): number of label types
        dropout (float): dropout to be applied to the layer
    """
    @staticmethod
    def create_ports():
        input_ports = {
            "hidden_states": NeuralType({
                0: AxisType(BatchTag),
                1: AxisType(TimeTag),
                2: AxisType(ChannelTag)
            })
        }

        output_ports = {
            "logits": NeuralType({
                0: AxisType(BatchTag),
                1: AxisType(ChannelTag)
            }),
        }
        return input_ports, output_ports

    def __init__(self,
                 hidden_size,
                 num_classes,
                 num_layers=2,
                 activation='relu',
                 log_softmax=True,
                 dropout=0.0,
                 use_transformer_pretrained=True):
        super().__init__()
        self.mlp = MultiLayerPerceptron(hidden_size,
                                        num_classes,
                                        self._device,
                                        num_layers,
                                        activation,
                                        log_softmax)
        self.dropout = nn.Dropout(dropout)
        if use_transformer_pretrained:
            self.apply(
                lambda module: transformer_weights_init(module, xavier=False))
        # self.to(self._device) # sometimes this is necessary

    def forward(self, hidden_states, idx_conditioned_on=0):
        hidden_states = self.dropout(hidden_states)
        logits = self.mlp(hidden_states[:, idx_conditioned_on])
        return logits


class JointIntentSlotClassifier(TrainableNM):
    """
    The softmax classifier for the joint intent classification and slot
    filling task.

    It consists of a dense layer + relu + softmax for predicting the slots
    and similar for predicting the intents.

    Args:
        hidden_size (int): the size of the hidden state for the dense layer
        num_intents (int): number of intents
        num_slots (int): number of slots
        dropout (float): dropout to be applied to the layer

    """
    @staticmethod
    def create_ports():
        input_ports = {
            "hidden_states": NeuralType({
                0: AxisType(BatchTag),
                1: AxisType(TimeTag),
                2: AxisType(ChannelTag)
            })
        }

        output_ports = {
            "intent_logits": NeuralType({
                0: AxisType(BatchTag),
                1: AxisType(ChannelTag)
            }),
            "slot_logits": NeuralType({
                0: AxisType(BatchTag),
                1: AxisType(TimeTag),
                2: AxisType(ChannelTag)
            })
        }
        return input_ports, output_ports

    def __init__(self,
                 hidden_size,
                 num_intents,
                 num_slots,
                 dropout=0.0,
                 use_transformer_pretrained=True):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        self.slot_mlp = MultiLayerPerceptron(hidden_size,
                                             num_classes=num_slots,
                                             device=self._device,
                                             num_layers=2,
                                             activation='relu',
                                             log_softmax=False)
        self.intent_mlp = MultiLayerPerceptron(hidden_size,
                                               num_classes=num_intents,
                                               device=self._device,
                                               num_layers=2,
                                               activation='relu',
                                               log_softmax=False)
        if use_transformer_pretrained:
            self.apply(
                lambda module: transformer_weights_init(module, xavier=False))
        # self.to(self._device)

    def forward(self, hidden_states):
        """ hidden_states: the outputs from the previous layers
        """
        hidden_states = self.dropout(hidden_states)

        intent_logits = self.intent_mlp(hidden_states[:, 0])
        slot_logits = self.slot_mlp(hidden_states)
        return intent_logits, slot_logits