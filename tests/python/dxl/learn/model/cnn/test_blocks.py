# _*_ encoding: utf-8 _*_

import tensorflow as tf 
import numpy as np
from dxl.learn.model.cnn import Conv2D, StackedConv2D, InceptionBlock, UnitBlock


class BlocksTest(tf.test.TestCase):
    def test_Conv2D(self):
        x = np.ones([1, 100, 100, 3], dtype="float32")
        conv2d_ins = Conv2D(
            name='Conv2D_test',
            input_tensor=tf.constant(x),
            filters=32,
            kernel_size=[5,5],
            strides=(2, 2),
            padding='same',
            activation='basic')
        y = conv2d_ins.outputs['main']
        with self.test_session() as sess:
            sess.run(tf.global_variables_initializer())
            y = sess.run(y)
            self.assertAllEqual(y.shape, (1, 50, 50, 32))

    def test_StackedConv2D(self):
        x = np.ones([1, 100, 100, 3], dtype="float32")
        stackedconv2d_ins = StackedConv2D(
            name='StackedConv2D_test',
            input_tensor=tf.constant(x),
            nb_layers=2,
            filters=32,
            kernel_size=[5,5],
            strides=(2, 2),
            padding='same',
            activation='basic')
        y = stackedconv2d_ins.outputs['main']
        with self.test_session() as sess:
            sess.run(tf.global_variables_initializer())
            y = sess.run(y)
            self.assertAllEqual(y.shape, (1, 25, 25, 32))

    def test_InceptionBlock(self):
        x = np.ones([2, 100, 100, 3], dtype="float32")
        inceptionblock_ins =  InceptionBlock(
            name='InceptionBlock_test',
            input_tensor=tf.constant(x),
            paths=3,
            activation='incept')
        y = inceptionblock_ins.outputs['main']
        with self.test_session() as sess:
            sess.run(tf.global_variables_initializer())
            y = sess.run(y)
            self.assertAllEqual(y.shape, (2, 100, 100, 3))
    
    def test_UnitBlock(self):
        x = np.ones([1, 100, 100, 3], dtype="float32")
        unitblock_ins = UnitBlock(
            name='UnitBlock_test',
            input_tensor=tf.constant(x))
        y = unitblock_ins.outputs['main']
        with self.test_session() as sess:
            sess.run(tf.global_variables_initializer())
            y = sess.run(y)
            self.assertAllEqual(y, x)


if __name__ == "__main__":
    tf.test.main()

