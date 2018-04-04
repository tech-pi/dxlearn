import tensorflow as tf
from typing import Dict


class Host:
  """
    Object saving host information.
    """

  def __init__(self, job: str, task: int = 0, ip: str = None,
               port: int = None):
    """
        Parameters:

        - `job`: A string of host type, like 'master', 'worker', 'ps', etc.
        - `task`: Index of correspoding node given specific cluster.
        - `ip`: ip, optional, if None, __eq__ will return True to host with any ip.
        - `port`: port, optional, if None, __eq__ will return True to host with any port.
        """
    self.job = job
    self.task = int(task)
    self.ip = ip
    self.port = port

  @property
  def job_name(self):
    return self.job

  @property
  def task_index(self):
    return self.task

  def device_prefix(self):
    return "/job:{}/task:{}".format(self.job, self.task)

  def __eq__(self, h: 'Host'):
    if self.job != h.job or self.task != h.task:
      return False
    if self.ip is not None and h.ip is not None and self.ip != h.ip:
      return False
    if self.port is not None and h.port is not None and self.port != h.port:
      return False
    return True


class Master:
  _master_host = None

  @classmethod
  def set_master(cls, job_name: str = None, task_index: int = None):
    if job_name is None:
      job_name = 'master'
    if task_index is None:
      task_index = 0
    if cls._master_host is not None:
      raise TypeError("Chief is already set.")
    cls._master_host = Host(job_name, task_index)

  @classmethod
  def master_host(cls):
    """
    Alias to master host.
    """
    return cls.host()

  @classmethod
  def host(cls):
    return cls._master_host

  @classmethod
  def is_master(cls, host: Host):
    return host == cls.master_host()


class ThisHost:
  _host: Host = None

  @classmethod
  def set_host(cls, job: str, task: int = 0, ip: str = None, port: int = None):
    cls._host = Host(job, task, ip, port)
    return cls._host

  @classmethod
  def host(cls):
    return cls._host

  @classmethod
  def is_me(cls, host: Host):
    return cls.host() == host

  @classmethod
  def is_master(cls):
    return Master.is_master(cls.host())


class Server:
  _server = None

  @classmethod
  def set_server(cls, config=None):
    if cls._server is not None:
      raise TypeError("Server is already constructed.")
    if Cluster.cluster() is None:
      raise TypeError("No cluster specification.")
    if ThisHost.host() is None:
      raise TypeError("No ThisHost specification")
    job = ThisHost.host().job
    task_index = ThisHost.host().task
    cluster = Cluster.cluster()

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    cls._server = tf.train.Server(
        cluster, job_name=job, task_index=task_index, config=config)
    return cls._server

  @classmethod
  def server(cls):
    return cls._server

  @classmethod
  def join(cls):
    if cls._server is None:
      raise TypeError("Server is not constructed yet.")
    return cls._server.join()


class Cluster:
  _cluster_spec = None
  _cluster = None
  _hosts = None

  @classmethod
  def dumps(cls):
    if cls._cluster_spec is None:
      return ""
    import json
    return json.dumps(
        cls._cluster_spec, indent=4, separators=(',', ': '), sort_keys=True)

  @classmethod
  def parse_config(cls, config) -> Dict[str, Dict]:
    if isinstance(config, dict):
      return config
    else:
      import json
      return json.loads(config)

  @classmethod
  def set_cluster(cls, config):
    if cls._cluster_spec is not None:
      msg = "Cluster spec already set:\n{}".format(cls.dumps())
      raise TypeError(msg)
    if cls._cluster is not None:
      raise TypeError("Cluster is already constructed.")
    cls._cluster_spec = cls.parse_config(config)
    cls._hosts = []
    for c, ws in cls._cluster_spec.items():
      if isinstance(ws, dict):
        for i, v in ws.items():
          ip, port = v.split(':')
          port = int(port)
          cls._hosts.append(Host(c, i, ip, port))
      else:
        for i, h in enumerate(ws):
          ip, port = h.split(':')
          port = int(port)
          cls._hosts.append(Host(c, i, ip, port))
    cls._hosts = tuple(cls._hosts)
    cls._cluster = tf.train.ClusterSpec(cls._cluster_spec)
    return cls._cluster

  @classmethod
  def cluster(cls):
    return cls._cluster

  @classmethod
  def hosts(cls):
    return tuple(cls._hosts)

  @classmethod
  def host(cls, job: str, task: int):
    for h in cls._cluster:
      if h == Host(job, task):
        return h
    return None


def make_distribute_host(cluster_config,
                         job,
                         task,
                         server_config=None,
                         master_job=None,
                         master_task_index=None):
  Cluster.set_cluster(cluster_config)
  ThisHost.set_host(job, task)
  Server.set_server(server_config)
  if master_job is not None:
    Master.set_master(master_job, master_task_index)
  return ThisHost.host()


class Barrier:
  def __init__(self, name, signal_hosts, join_hosts, task_lists=()):
    """
        `task_lists`: tasks to be run on signal_hosts, which is a list of taks list,
        as shown below:
        [
            [t0_of_signal_host_0, t1_of_signal_host_0,...],
            [t0_of_signal_host_1, t1_of_singal_host_1,...],
            ...
        ]
        
        This barrier can sync *multiple* tasks run on *multiple* signal hosts
        and serve for *multiple* join hosts.

        Each join host has a queue, and required to dequeue # of tokens equal
        to len(taks_lists)

        Each signal host enqueue one token for eqah queue of join hots.
        """
    self.name = name
    self.signal_hosts = signal_hosts
    self.join_hosts = join_hosts
    self.task_lists = task_lists
    self.signal_ops, self.join_ops = self.construct()

  def _make_queues_and_join_ops_for_join_hosts(self):
    # queues is 1:1 to join hosts
    names = [
        "{}_{}".format(self.name, i) for i, _ in enumerate(self.join_hosts)
    ]
    queues = [
        tf.FIFOQueue(
            len(self.signal_hosts), tf.bool, [], name=n, shared_name=n)
        for n, _ in zip(names, self.join_hosts)
    ]
    # join op is barried by dequeue nb_single tokens
    join_ops = [q.dequeue_many(len(self.signal_hosts)) for q in queues]
    return join_ops, queues

  def _make_signal_ops(self, queues):
    from .utils import map_data
    # Expand tasks to tf.Tensor or Op
    task_lists = [map_data(tl) for tl in self.task_lists]

    def make_signal_op_for_one_signal_host(task_list):
      with tf.control_dependencies(task_list):
        _ops = [q.enqueue(False) for q in queues]
      with tf.control_dependencies(_ops):
        return tf.no_op()

    signal_ops = [make_signal_op_for_one_signal_host(tl) for tl in task_lists]
    return signal_ops

  def construct(self):
    with tf.name_scope(self.name):
      join_ops, queues = self._make_queues_and_join_ops_for_join_hosts()
      signal_ops = self._make_signal_ops(queues)
    return signal_ops, join_ops

  def barrier(self, host):
    if host in self.signal_hosts:
      return self.signal_ops[self.signal_hosts.index(host)]
    elif host in self.join_hosts:
      return self.join_ops[self.join_hosts.index(host)]
    else:
      return tf.no_op()

  def run(self):
    from .session import ThisSession
    ThisSession.run(self.barrier(ThisHost.host()))


class DistributeTask:
  """
  Helper class of managing distribute run.
  """

  def __init__(self, distribute_configs):
    self.cfg = distribute_configs
    self.master_graph = None
    self.worker_graphs = []
    self.master_host = None
    self.hosts = []
    self.master_graph_info = None

  def cluster_init(self, job, task):
    from .graph_info import DistributeGraphInfo
    make_distribute_host(self.cfg, job, task, None, 'master', 0)
    self.master_host = Master.master_host()
    self.hosts = [Host('worker', i) for i in range(NB_WORKERS)]
    self.master_graph_info = DistributeGraphInfo(None, None, None, master_host)
    self.worker_graph_infos = [
        DistributeGraphInfo(None, None, None, h) for h in self.hosts
    ]
  
  def nb_workers(self):
    return len(self.hosts)

  def add_master_graph(self, g):
    self.master_graph = g

  def add_worker_graph(self, g):
    self.worker_graphs.append(g)

  def add_host(self, h):
    self.hosts.append(h)

  def worker_graph_on(self, host: Host):
    return self.worker_graphs[host.task_index]

  def graph_on_this_host(self):
    host = ThisHost.host()
    if ThisHost.is_master():
      return self.master_graph
    else:
      for g in local_graphs:
        if g.graph_info.host == host:
          return g
    raise KeyError("No local graph for {}.{} found".format(
        host.job, host.task_index))

  def ginfo_master(self):
    return self.master_graph_info
  
  def ginfo_worker(self, task_index):
    return self.worker_graph_infos[task_index]

  def ginfo_this(self):
    from .graph_info import DistributeGraphInfo
    return DistributeGraphInfo(None, None, None, ThisHost.host())
  
    
