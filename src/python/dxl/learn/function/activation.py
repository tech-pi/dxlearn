from doufo import singledispatch
import tensorflow as tf
from dxl.learn.core import Tensor

__all__ = ['relu', 'selu', 'swish', 'elu']


@singledispatch(nargs=1, nouts=1)
def relu(x):
    raise NotImplementedError("relu not implemented for {}.".format(type(x)))


@relu.register(Tensor)
def _(x):
    return x.fmap(relu)


@relu.register(tf.Tensor)
def _(x):
    with tf.variable_scope('relu'):
        return tf.nn.relu(x)


@singledispatch(nargs=1, nouts=1)
def selu(x):
    raise NotImplementedError("SELU not implemented for {}.".format(type(x)))


@selu.register(tf.Tensor)
def _(x):
    with tf.variable_scope('selu'):
        alpha = 1.6732632437728481704
        scale = 1.0507009873554804933
        return scale * tf.where(x >= 0, x, alpha * tf.nn.elu(x))


@selu.register(Tensor)
def _(x):
    return x.fmap(selu)


@singledispatch(nargs=1, nouts=1)
def swish(x):
    raise NotImplementedError("swish not implemented for {}.".format(type(x)))


@swish.register(tf.Tensor)
def _(x):
    with tf.variable_scope('swish', x):
        return x * tf.nn.sigmoid(x)


@swish.register(Tensor)
def _(x):
    return x.fmap(swish)


@singledispatch(nargs=1, nouts=1)
def elu(x):
    raise NotImplementedError("ELU not implemented for {}.".format(type(x)))


@elu.register(tf.Tensor)
def _(x):
    with tf.variable_scope('elu'):
        return tf.nn.elu(x)


@elu.register(Tensor)
def _(x):
    return x.fmap(elu)
