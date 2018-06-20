import tensorflow as tf
import numpy as np
from dxl.learn.model.stack import Stack, StackedConv2D
from dxl.learn.test import TestCase, UnitBlock


class TestStack(TestCase):
    def get_input(self):
        return np.ones([1, 100, 100, 3], dtype="float32")

    def make_model(self):
        return UnitBlock("unitblock_test")

    def test_Stack(self):
        x = self.get_input()
        nb_layer = 2
        y_ = x

        stack_ins = Stack(
            'Stack_test', tf.constant(x), self.make_model(), nb_layer)
        y = stack_ins()
        with self.variables_initialized_test_session() as sess:
            y = sess.run(y)
            self.assertAllEqual(y, y_)

        