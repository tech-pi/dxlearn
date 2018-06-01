# -*- coding: utf-8 -*-

import tensorflow as tf
import numpy as np
from fs import path as fp
from .blocks import Conv2D, StackedConv2D, InceptionBlock, UnitBlock
from ...core import Model
from ...core import Tensor

__all__ = [
    'ResidualIncept', 'ResidualStackedConv', 'StackedResidualIncept',
    'StackedResidualConv'
]


class ResidualIncept(Model):
    """ResidualIncept Block
    Arguments:
        name: Path := dxl.fs.
        input_tensor: Tensor input.
        ratio: The decimal.
        sub_block: InceptionBlock instance.
        graph_info: GraphInfo or DistributeGraphInfo
    """

    class KEYS(Model.KEYS):
        class TENSOR(Model.KEYS.TENSOR):
            pass

        class CONFIG:
            RATIO = 'ratio'

        class SUB_BLOCK:
            INCEPTION = 'InceptionBlock'

    def __init__(self,
                 info,
                 input_tensor=None,
                 ratio=None,
                 sub_block: InceptionBlock = None):
        super().__init__(
            info,
            inputs={self.KEYS.TENSOR.INPUT: input_tensor},
            submodels={self.KEYS.SUB_BLOCK.INCEPTION: sub_block},
            config={
                self.KEYS.CONFIG.RATIO: ratio,
            })

    @classmethod
    def default_config(cls):
        return {cls.KEYS.CONFIG.RATIO: 0.3}

    @classmethod
    def sub_block_maker(cls, graph, name, input_tensor):
        sub_block = InceptionBlock(
            graph.info.child(name),
            input_tensor=input_tensor,
            paths=3,
            activation='incept')

        return sub_block

    def kernel(self, inputs):
        x = inputs[self.KEYS.TENSOR.INPUT]
        sub_block = self.subgraph(
            self.KEYS.SUB_BLOCK.INCEPTION,
            lambda p, k: ResidualIncept.sub_block_maker(p, k, x))
        h = sub_block(inputs)
        with tf.name_scope('add'):
            x = x + h * self.config(self.KEYS.CONFIG.RATIO)
        return x


class ResidualStackedConv(Model):
    """ ResidualStackedConv Block
    Arguments:
        name: Path := dxl.fs.
        input_tensor: Tensor input.
        ratio: The decimal.
        sub_block: StackedConv2D instance.
        graph_info: GraphInfo or DistributeGraphInfo
    """

    class KEYS(Model.KEYS):
        class TENSOR(Model.KEYS.TENSOR):
            pass

        class CONFIG:
            RATIO = 'ratio'

        class SUB_BLOCK:
            STK_CONV2D = 'StackedConv2D'

    def __init__(self,
                 info,
                 input_tensor=None,
                 ratio=None,
                 sub_block: StackedConv2D = None):
        super().__init__(
            info,
            inputs={self.KEYS.TENSOR.INPUT: input_tensor},
            submodels={self.KEYS.SUB_BLOCK.STK_CONV2D: sub_block},
            config={self.KEYS.CONFIG.RATIO: ratio})

    @classmethod
    def default_config(cls):
        return {cls.KEYS.CONFIG.RATIO: 0.1}

    @classmethod
    def sub_block_maker(cls, graph, name, input_tensor):
        return StackedConv2D(
            graph.info.child(name),
            input_tensor=input_tensor,
            nb_layers=2,
            filters=1,
            kernel_size=(1, 1),
            strides=(1, 1),
            padding='same',
            activation='basic')

    def kernel(self, inputs):
        x = inputs[self.KEYS.TENSOR.INPUT]
        sub_block = self.subgraph(
            self.KEYS.SUB_BLOCK.STK_CONV2D,
            lambda p, k: ResidualStackedConv.sub_block_maker(p, k, x))
        h = sub_block(inputs)
        with tf.name_scope('add'):
            x = x + h * self.config(self.KEYS.CONFIG.RATIO)
        return x


class StackedResidualIncept(Model):
    """StackedResidual Block
    Arguments:
        name: Path := dxl.fs.
        input_tensor: Tensor input.
        nb_layers: Integer.
        sub_block: ResidualIncept Instance.
        graph_info: GraphInfo or DistributeGraphInfo
    """

    class KEYS(Model.KEYS):
        class TENSOR(Model.KEYS.TENSOR):
            pass

        class CONFIG:
            NB_LAYERS = 'nb_layers'

        class SUB_BLOCK:
            RES_INCEPT = 'ResidualIncept'

    def __init__(self,
                 info,
                 input_tensor=None,
                 nb_layers=None,
                 sub_block: ResidualIncept = None):
        super().__init__(
            info,
            inputs={self.KEYS.TENSOR.INPUT: input_tensor},
            submodels={self.KEYS.SUB_BLOCK.RES_INCEPT: sub_block},
            config={self.KEYS.CONFIG.NB_LAYERS: nb_layers})

    @classmethod
    def default_config(cls):
        return {cls.KEYS.CONFIG.NB_LAYERS: 2}

    @classmethod
    def sub_block_maker(cls, preblock, subkey, input_tensor):
        sub_block = ResidualIncept(
            preblock.info.child(subkey), input_tensor=input_tensor, ratio=0.3)

        return sub_block

    def kernel(self, inputs):
        x = inputs[self.KEYS.TENSOR.INPUT]
        for i in range(self.config(self.KEYS.CONFIG.NB_LAYERS)):
            sub_block = self.subgraph(
                self.KEYS.SUB_BLOCK.RES_INCEPT,
                lambda p, k: StackedResidualIncept.sub_block_maker(p, k, x))
            x = sub_block(inputs)
        return x


class StackedResidualConv(Model):
    """StackedResidual Block
    Arguments:
        name: Path := dxl.fs.
        input_tensor: Tensor input.
        nb_layers: Integer.
        sub_block: ResidualStackedConv Instance.
        graph_info: GraphInfo or DistributeGraphInfo
    """

    class KEYS(Model.KEYS):
        class TENSOR(Model.KEYS.TENSOR):
            pass

        class CONFIG:
            NB_LAYERS = 'nb_layers'

        class SUB_BLOCK:
            RES_STACKEDCONV = 'ResidualStackedConv'

    def __init__(self,
                 info,
                 input_tensor=None,
                 nb_layers=None,
                 sub_block: ResidualStackedConv = None):
        super().__init__(
            info,
            inputs={self.KEYS.TENSOR.INPUT: input_tensor},
            submodels={self.KEYS.SUB_BLOCK.RES_STACKEDCONV: sub_block},
            config={self.KEYS.CONFIG.NB_LAYERS: nb_layers})

    @classmethod
    def default_config(cls):
        return {cls.KEYS.CONFIG.NB_LAYERS: 2}

    @classmethod
    def sub_block_maker(cls, preblock, subkey, input_tensor, id_block):
        sub_block = ResidualStackedConv(
            preblock.info.child(subkey), input_tensor=input_tensor, ratio=0.1)

        return sub_block

    def kernel(self, inputs):
        x = inputs[self.KEYS.TENSOR.INPUT]
        for i in range(self.config(self.KEYS.CONFIG.NB_LAYERS)):
            sub_block = self.subgraph(
                "{}_{}".format(self.KEYS.SUB_BLOCK.RES_STACKEDCONV, i),
                lambda p, k: StackedResidualConv.sub_block_maker(p, k, x, i))
            x = sub_block(x)
        return x
