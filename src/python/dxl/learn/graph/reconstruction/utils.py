import numpy as np
import h5py
import tensorflow as tf
from ...core import ThisHost
import json
import logging

logging.basicConfig(
    format='[%(levelname)s] %(asctime)s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%a, %d %b %Y %H:%M:%S',
)
logger = logging.getLogger('dxl.learn.graph.reconstruction')


class ImageInfo:
  def __init__(self, grid, center, size):
    self.grid = grid
    self.center = center
    self.size = size


class DataInfo:
  def __init__(self,
               map_file,
               lor_files,
               lor_shapes,
               lor_ranges=None,
               lor_step=None):
    self._map_file = map_file
    self._lor_files = lor_files
    self._lor_shapes = lor_shapes
    self._lor_ranges = lor_ranges
    self._lor_step = lor_step

  def _maybe_broadcast_value(self,
                             value,
                             task_index=None,
                             valid_type=(list, tuple)):
    if task_index is None:
      task_index = ThisHos
    if isinstance(value, valid_type):
      return value[task_index]
    else:
      return value

  def map_file(self, task_index=None):
    if task_index is None:
      task_index = ThisHost.host().task_index
    if isinstance(self._map_file, str):
      return self._map_file
    else:
      return self._map_file[task_index]

  def lor_file(self, axis, task_index=None):
    if task_index is None:
      task_index = ThisHost().host().task_index
    if isinstance(self._lor_files[axis], str):
      return self._lor_files[axis]
    else:
      return self._lor_files[axis][task_index]

  def lor_range(self, axis, task_index=None):
    if task_index is None:
      task_index = ThisHost.host().task_index
    if self._lor_ranges is not None:
      return self._maybe_broadcast_value(self._lor_ranges[axis], task_index)
    elif self._lor_step is not None:
      step = self._maybe_broadcast_value(self._lor_step[axis], task_index)
      return [task_index * step, (task_index + 1) * step]
    else:
      return None

  def lor_shape(self, axis, task_index=None):
    if task_index is None:
      task_index = ThisHost().host().task_index
    if isinstance(self._lor_shapes[axis], (list, tuple)):
      return self._lor_shapes[axis]
    else:
      return self._lor_shapes[axis][task_index]

  def __str__(self):
    result = {}
    axis = ['x', 'y', 'z']
    result['map_file'] = self.map_file()
    result['lor_file'] = {a: self.lor_file(a) for a in axis}
    result['lor_range'] = {a: self.lor_range(a) for a in axis}
    result['lor_shape'] = {a: self.lor_shape(a) for a in axis}
    return json.dumps(result, indent=4, separators=(',', ': '))


def load_data(file_name, lor_range=None):
  if file_name.endswith('.npy'):
    data = np.load(file_name)
    if lor_range is not None:
      data = data[lor_range[0]:lor_range[1], :]
  elif file_name.endswith('.h5'):
    with h5py.File(file_name, 'r') as fin:
      if lor_range is not None:
        data = np.array(fin['data'][lor_range[0]:lor_range[1], :])
      else:
        data = np.array(fin['data'])
  return data


# Load datas
def load_local_data(data_info: DataInfo, task_index):
  logger.info("Loading efficiency map from file: {}...".format(
      data_info.map_file()))
  emap = load_data(data_info.map_file())
  lors = {}
  for a in ['x', 'y', 'z']:
    msg = "Loading {} LORs from file: {}, with range: {}..."
    logger.info(msg.format(a, data_info.lor_file(a), data_info.lor_range(a)))
    lors[a] = load_data(data_info.lor_file(a), data_info.lor_range(a))
  logger.info('Loading local data done.')
  return emap, lors


def ensure_float32(x):
  if isinstance(x, np.ndarray) and x.dtype == np.float64:
    return np.array(x, dtype=np.float32)
  return x


def constant_tensor(x, name, ginfo):
  return TensorNumpyNDArray(_ensure_float32(x), None, ginfo.update(name=name))


def variable_tensor(x, name, ginfo):
  x_tensor = TensorVariable(
      VariableInfo(None, _ensure_float32(x), tf.float32),
      ginfo.update(name=name))
  x_init = x_tensor.assign(_constant_tensor(x, name + '_initial_value', ginfo))
  return x_tensor, x_init


def print_tensor(t, name=None):
  print("[DEBUG] name: {}, tensor: {}, value:\n{}".format(
      name, t.data, t.run()))


def debug_tensor(t, msg):
  logger.debug("Debug {}, tensor: {}, (.data: {}):\n{}".format(
      msg, t, t.data, t.run()))


def print_info(*msg):
  print('INFO', *msg)


sample_reconstruction_config = {
    'grid': [150, 150, 150],
    'center': [0., 0., 0.],
    'size': [150., 150., 150.],
    'map_file': './debug/map.npy',
    'x_lor_files': './debug/xlors.npy',
    'y_lor_files': './debug/ylors.npy',
    'z_lor_files': './debug/zlors.npy',
    'x_lor_shapes': [100, 6],
    'y_lor_shapes': [200, 6],
    'z_lor_shapes': [300, 6],
    'lor_ranges': None,
    'lor_steps': None,
}


def load_reconstruction_configs(config=None):
  if config is None:
    c = sample_reconstruction_config
  elif isinstance(config, str):
    with open(config, 'r') as fin:
      c = json.load(fin)
  else:
    c = config
  image_info = ImageInfo(c['grid'], c['center'], c['size'])
  data_info = DataInfo(
      c['map_file'], {a: c['{}_lor_files'.format(a)]
                      for a in ['x', 'y', 'z']},
      {a: c['{}_lor_shapes'.format(a)]
       for a in ['x', 'y', 'z']}, c['lor_ranges'], c['lor_steps'])
  return image_info, data_info